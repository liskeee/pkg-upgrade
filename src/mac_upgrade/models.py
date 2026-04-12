from dataclasses import dataclass


@dataclass
class Package:
    name: str
    current_version: str
    latest_version: str

    def __str__(self) -> str:
        return f"{self.name} {self.current_version} -> {self.latest_version}"


@dataclass
class Result:
    success: bool
    message: str
    package: Package
