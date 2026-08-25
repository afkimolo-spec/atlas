from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class ResourcePriority(IntEnum):
    LOW = 10
    NORMAL = 50
    HIGH = 75
    CRITICAL = 100


class ResourceConflictError(RuntimeError):
    """Raised when a resource cannot be acquired."""


@dataclass(slots=True)
class Resource:
    name: str
    capacity: int = 1
    available: int = field(init=False)

    def __post_init__(self) -> None:
        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Resource name cannot be empty.")

        if self.capacity < 1:
            raise ValueError("Resource capacity must be at least 1.")

        self.available = self.capacity


@dataclass(slots=True)
class ResourceLease:
    resource: str
    owner: str
    priority: ResourcePriority
    units: int = 1


@dataclass(slots=True)
class ResourceManager:
    """
    Deterministic in-process resource manager.

    Resources have finite capacity. Acquisition is exclusive up to
    the configured capacity and is released explicitly.
    """

    resources: dict[str, Resource] = field(default_factory=dict)
    leases: dict[str, list[ResourceLease]] = field(
        default_factory=dict
    )

    def register(
        self,
        name: str,
        *,
        capacity: int = 1,
    ) -> Resource:
        if name in self.resources:
            raise ValueError(
                f"Resource already registered: {name}"
            )

        resource = Resource(
            name=name,
            capacity=capacity,
        )

        self.resources[resource.name] = resource
        self.leases[resource.name] = []

        return resource

    def get(self, name: str) -> Resource:
        try:
            return self.resources[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown resource: {name}"
            ) from exc

    def available(self, name: str) -> int:
        return self.get(name).available

    def can_acquire(
        self,
        name: str,
        *,
        units: int = 1,
    ) -> bool:
        if units < 1:
            raise ValueError("units must be at least 1.")

        return self.available(name) >= units

    def acquire(
        self,
        name: str,
        owner: str,
        *,
        units: int = 1,
        priority: ResourcePriority = ResourcePriority.NORMAL,
    ) -> ResourceLease:
        owner = owner.strip()

        if not owner:
            raise ValueError("Resource owner cannot be empty.")

        if units < 1:
            raise ValueError("units must be at least 1.")

        resource = self.get(name)

        if resource.available < units:
            raise ResourceConflictError(
                f"Resource '{name}' unavailable for owner "
                f"'{owner}': requested {units}, "
                f"available {resource.available}."
            )

        lease = ResourceLease(
            resource=name,
            owner=owner,
            priority=priority,
            units=units,
        )

        resource.available -= units
        self.leases[name].append(lease)

        self.leases[name].sort(
            key=lambda item: (
                -int(item.priority),
                item.owner,
            )
        )

        return lease

    def release(
        self,
        lease: ResourceLease,
    ) -> None:
        resource = self.get(lease.resource)
        active = self.leases[lease.resource]

        try:
            active.remove(lease)
        except ValueError as exc:
            raise ResourceConflictError(
                f"Lease is not active: {lease.owner}"
            ) from exc

        resource.available += lease.units

        if resource.available > resource.capacity:
            raise RuntimeError(
                f"Resource accounting overflow: {resource.name}"
            )

    def release_owner(self, owner: str) -> int:
        released = 0

        for name, leases in self.leases.items():
            resource = self.resources[name]

            remaining = []

            for lease in leases:
                if lease.owner == owner:
                    resource.available += lease.units
                    released += lease.units
                else:
                    remaining.append(lease)

            self.leases[name] = remaining

        return released

    def snapshot(self) -> dict:
        return {
            "resources": {
                name: {
                    "capacity": resource.capacity,
                    "available": resource.available,
                }
                for name, resource in self.resources.items()
            },
            "leases": {
                name: [
                    {
                        "owner": lease.owner,
                        "priority": int(lease.priority),
                        "units": lease.units,
                    }
                    for lease in leases
                ]
                for name, leases in self.leases.items()
            },
        }
