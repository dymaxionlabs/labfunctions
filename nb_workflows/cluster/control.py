from copy import deepcopy
from typing import Any, Dict, List, Optional, Set

import redis
from rq import Queue

from nb_workflows.control_plane.register import AgentRegister
from nb_workflows.types import ServerSettings
from nb_workflows.types.agent import AgentNode
from nb_workflows.types.cluster import (
    ClusterDiff,
    ClusterFile,
    ClusterPolicy,
    ClusterSpec,
    ClusterState,
    ScaleIdle,
    ScaleItems,
)
from nb_workflows.types.machine import (
    ExecMachineResult,
    ExecutionMachine,
    MachineInstance,
)
from nb_workflows.utils import open_yaml

from . import deploy
from .base import ProviderSpec
from .context import machine_from_settings
from .inventory import Inventory


def apply_scale_items(state: ClusterState, scale: ScaleItems) -> ClusterState:
    new_state = deepcopy(state)
    if state.queue_items[scale.qname] >= scale.items_gt:
        new_state.agents_n += scale.increase_by
    elif state.queue_items[scale.qname] <= scale.items_lt:
        new_state.agents_n -= scale.decrease_by
        new_state.agents.pop()

    return new_state


def apply_idle(state: ClusterState, idle: ScaleIdle) -> ClusterState:
    new_state = deepcopy(state)
    shutdown_agents = set()
    for agt in state.agents:
        if state.idle_by_agent[agt] >= idle.idle_time_gt:
            shutdown_agents.add(agt)
    agents = state.agents - shutdown_agents

    new_state.agents = agents
    new_state.agents_n = len(agents)
    return new_state


def apply_minmax(state: ClusterState, policy: ClusterPolicy) -> ClusterState:
    new_state = deepcopy(state)
    if state.agents_n < policy.min_nodes:
        new_state.agents_n = policy.min_nodes
    elif state.agents_n > policy.max_nodes:
        new_state.agents_n = policy.max_nodes

    return new_state


class ClusterControl:

    POLICIES = {
        "items": apply_scale_items,
        "idle": apply_idle,
        # "minmax": apply_minmax
    }
    STRATEGIES = {"items": ScaleItems, "idle": ScaleIdle}

    def __init__(self, rdb: redis.Redis, spec: ClusterSpec, inventory: Inventory):
        self.rdb = rdb
        self.name = spec.name
        self.spec = spec
        self.inventory = inventory
        self.register = AgentRegister(rdb, cluster=spec.name)
        self.state = self.build_state()

    @property
    def cluster_name(self):
        return self.name

    def get_provider(self) -> ProviderSpec:
        return self.inventory.get_provider(self.spec.provider)

    @classmethod
    def load_spec(cls, spec_data) -> ClusterSpec:
        c = ClusterSpec(**spec_data)
        strategies = []
        for strategy in c.policy.strategies:
            s = cls.STRATEGIES[strategy["name"]](**strategy)
            strategies.append(s)
        c.policy.strategies = strategies
        return c

    @classmethod
    def load_cluster_file(cls, yaml_path) -> ClusterFile:
        data = open_yaml(yaml_path)
        clusters = {}
        for k, v in data["clusters"].items():
            spec = cls.load_spec(v)
            clusters[k] = spec
        inventory = data.get("inventory")

        return ClusterFile(clusters=clusters, inventory=inventory)

    def refresh(self):
        self.state = self.build_state()

    def build_state(self) -> ClusterState:
        agents = self.register.list_agents(self.name)
        # agents_obj = {self.register.get(a) for a in agents}
        agents_n = len(agents)
        queues_obj: List[Queue] = [self.register.get_queue(q) for q in self.spec.qnames]
        queue_items = {q.name: len(q) for q in queues_obj}

        idle_by_agent = self.register.idle_agents(agents, queues_obj)

        return ClusterState(
            agents_n=agents_n,
            agents=set(agents),
            queue_items=queue_items,
            idle_by_agent=idle_by_agent,
        )

    @property
    def policy(self) -> ClusterPolicy:
        return self.spec.policy

    def apply_policies(self):
        new_state = self.state.copy()
        for scale in self.policy.strategies:
            new_state = self.POLICIES[scale.name](new_state, scale)

        new_state = apply_minmax(new_state, self.policy)

        return new_state

    def difference(self, new_state: ClusterState) -> ClusterDiff:

        to_delete = self.state.agents - new_state.agents

        to_create = 0
        if new_state.agents_n > self.state.agents_n:
            to_create = new_state.agents_n - self.state.agents_n

        if len(new_state.agents) < self.policy.min_nodes:
            to_create = self.policy.min_nodes - len(new_state.agents)

        return ClusterDiff(to_create=to_create, to_delete=list(to_delete))

    def create_instance(
        self,
        provider: ProviderSpec,
        settings: ServerSettings,
        do_deploy=True,
        use_public=False,
        deploy_local=False,
    ) -> MachineInstance:
        ctx = machine_from_settings(
            self.spec.machine,
            cluster=self.name,
            qnames=self.spec.qnames,
            settings=settings,
            inventory=self.inventory,
        )
        print(f"Creating machine: {ctx.machine.name}")
        instance = provider.create_machine(ctx.machine)
        ip = instance.private_ips[0]
        if use_public:
            ip = instance.public_ips[0]
        req = deploy.agent_from_settings(
            ip,
            instance.machine_id,
            self.name,
            settings,
            qnames=ctx.qnames,
            worker_procs=ctx.worker_procs,
            docker_version=ctx.docker_version,
        )
        if do_deploy and deploy_local:
            res = deploy.agent_local(req, settings.dict())
            print(res)
        elif do_deploy:
            res = deploy.agent(req, settings.dict())
            print(res)
        self.register.register_machine(instance)
        return instance

    def destroy_instance(self, provider: ProviderSpec, agent_name: str):
        agent = self.register.get(agent_name)
        if agent:
            self.register.kill_workers_from_agent(agent.name)
            machine = self.register.get_machine(agent.machine_id)
            self.register.unregister(agent)
            self.register.unregister_machine(agent.machine_id)
        else:
            machine = agent_name
        provider.destroy_machine(machine)

    def scale(
        self,
        provider: ProviderSpec,
        settings: ServerSettings,
        use_public=False,
        deploy_local=False,
    ):
        new_state = self.apply_policies()
        diff = self.difference(new_state)

        print(f"To create: {diff.to_create}")
        for _ in range(diff.to_create):
            self.create_instance(
                provider, settings, use_public=use_public, deploy_local=deploy_local
            )

        for agt in diff.to_delete:
            print(f"Deleting agent {agt}")
            self.destroy_instance(provider, agt)