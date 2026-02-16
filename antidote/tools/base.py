from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str | None = None


class BaseTool(ABC):
    name: str  # Unique identifier (e.g., "read_file")
    description: str  # Shown to LLM -- what does this tool do?
    parameters: dict  # JSON Schema for inputs

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Run the tool with given parameters. Return result."""
        ...
