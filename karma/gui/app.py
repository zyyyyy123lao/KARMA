"""Main GUI application for KARMA.

A Tkinter-based interface for entering tasks, monitoring execution,
managing task history, and viewing/ editing short-term memory.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import tkinter as tk
from tkinter import messagebox, scrolledtext

from karma.config import Config
from karma.planning.planner import LLMPlanner
from karma.planning.executor import TaskExecutor

logger = logging.getLogger("karma.gui.app")


# Full list of AI2-THOR object types for similarity checking
AI2THOR_OBJECTS = [
    "AlarmClock", "AluminumFoil", "Apple", "AppleSliced", "BaseballBat",
    "BasketBall", "Bathtub", "BathtubBasin", "Bed", "Blinds", "Book",
    "Boots", "Bottle", "Bowl", "Box", "Bread", "BreadSliced",
    "ButterKnife", "Candle", "CD", "CellPhone", "Cloth", "CoffeeMachine",
    "CreditCard", "Cup", "Curtains", "DeskLamp", "DishSponge", "DogBed",
    "Drawer", "Dresser", "Dumbbell", "Egg", "EggCracked", "FloorLamp",
    "Footstool", "Fork", "GarbageBag", "HandTowel", "HandTowelHolder",
    "HousePlant", "Kettle", "KeyChain", "Knife", "Ladle", "Laptop",
    "LaundryHamper", "Lettuce", "LettuceSliced", "LightSwitch",
    "Microwave", "Mirror", "Mug", "Newspaper", "Ottoman", "Painting",
    "Pan", "PaperTowelRoll", "Pen", "Pencil", "PepperShaker", "Pillow",
    "Plate", "Plunger", "Poster", "Pot", "Potato", "PotatoSliced",
    "RemoteControl", "RoomDecor", "Safe", "SaltShaker", "ScrubBrush",
    "Shelf", "ShelvingUnit", "ShowerCurtain", "ShowerDoor", "ShowerGlass",
    "ShowerHead", "Sink", "SinkBasin", "SoapBar", "SoapBottle", "Sofa",
    "Spatula", "Spoon", "SprayBottle", "Statue", "Stool", "StoveBurner",
    "StoveKnob", "TableTopDecor", "TargetCircle", "TeddyBear",
    "Television", "TennisRacket", "TissueBox", "Toaster", "Toilet",
    "ToiletPaper", "ToiletPaperHanger", "Tomato", "TomatoSliced",
    "Towel", "TowelHolder", "TVStand", "VacuumCleaner", "Vase", "Watch",
    "WateringCan", "Window", "WineBottle",
]


class KARMAApp:
    """Main Tkinter application for KARMA.

    Provides:
    - Task input field
    - Task history listbox
    - Similarity indicator (memory match)
    - Short-term memory viewer/editor
    - Start, clear, exit buttons
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.get_instance()
        self.paths = self.config.paths

        self._root = tk.Tk()
        self._root.title("KARMA - Embodied AI Agent")
        self._root.geometry("1000x950")

        self._task_history: list = self._load_history()
        self._similarity_flag = False

        self._setup_ui()
        self._populate_history()

    # ─── UI Setup ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build all UI components."""
        font_large = ("Helvetica", 16)
        font_med = ("Helvetica", 13)

        # Title
        title = tk.Label(
            self._root,
            text="KARMA - Embodied AI Agent",
            font=("Helvetica", 20, "bold"),
        )
        title.pack(pady=15)

        # Task input
        tk.Label(
            self._root,
            text="Enter task for the robot:",
            font=font_large,
        ).pack(pady=5)

        self._task_entry = tk.Entry(self._root, width=90, font=font_large)
        self._task_entry.pack(pady=10)

        # Buttons row
        btn_frame = tk.Frame(self._root)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="Start Task",
            font=font_large,
            command=self._on_start_task,
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Clear History",
            font=font_large,
            command=self._on_clear_history,
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Exit",
            font=font_large,
            command=self._on_exit,
            width=10,
        ).pack(side=tk.LEFT, padx=5)

        # Task history
        tk.Label(
            self._root,
            text="Task History:",
            font=font_large,
        ).pack(pady=5)

        self._history_listbox = tk.Listbox(
            self._root, width=90, height=8, font=font_med
        )
        self._history_listbox.pack(pady=5)

        scroll_history = tk.Scrollbar(self._root, command=self._history_listbox.yview)
        self._history_listbox.config(yscrollcommand=scroll_history.set)
        scroll_history.pack(fill=tk.Y, side=tk.RIGHT)

        # Similarity label
        self._similarity_var = tk.StringVar(value="")
        tk.Label(
            self._root,
            textvariable=self._similarity_var,
            font=font_large,
            fg="red",
        ).pack(pady=5)

        # Short-term memory
        tk.Label(
            self._root,
            text="Short-term Memory:",
            font=font_large,
        ).pack(pady=5)

        self._memory_text = scrolledtext.ScrolledText(
            self._root, width=90, height=8, font=font_med
        )
        self._memory_text.pack(pady=5)

        mem_btn_frame = tk.Frame(self._root)
        mem_btn_frame.pack(pady=5)

        tk.Button(
            mem_btn_frame,
            text="Load Memory",
            font=font_med,
            command=self._on_load_memory,
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            mem_btn_frame,
            text="Save Memory",
            font=font_med,
            command=self._on_save_memory,
        ).pack(side=tk.LEFT, padx=5)

        # Set initial focus to task entry
        self._task_entry.focus_force()
        self._task_entry.bind("<Return>", lambda _: self._on_start_task())

    # ─── Actions ─────────────────────────────────────────────────────────────

    def _on_start_task(self) -> None:
        """Handle Start Task button."""
        task = self._task_entry.get().strip()
        if not task:
            messagebox.showwarning("Input Error", "Please enter a task.")
            return

        # Save task description
        self._save_task_description(task)

        # Check similarity with history
        self._check_similarity(task)

        # Save to history
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"{task} ({timestamp})"
        self._task_history.append(entry)
        self._save_history()
        self._history_listbox.insert(tk.END, entry)

        # Prepare instruction file for LLM
        self._save_instruction(task)

        messagebox.showinfo("Info", "Starting task. Check terminal for progress.")

        # Run the pipeline
        self._run_task(task)

    def _run_task(self, task: str) -> None:
        """Execute the task pipeline.

        This runs in a separate thread to avoid blocking the GUI.
        """
        import threading

        def worker():
            try:
                from karma.planning import LLMPlanner
                from karma.agents import Robot, AI2ThorController, ActionExecutor

                planner = LLMPlanner(self.config)
                controller = AI2ThorController(self.config.agent)
                controller.initialize()

                # Create robot with ActionExecutor that saves/renders frames
                robot = Robot(controller, name=self.config.agent.name)
                robot._action_executor.save_frames = True

                planner.plan_and_execute(task, robot)

                robot._action_executor.stop()
                controller.close()
            except Exception as e:
                logger.error("Task execution failed: %s", e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_clear_history(self) -> None:
        """Clear task history."""
        self._task_history = []
        self._save_history()
        self._history_listbox.delete(0, tk.END)
        self._similarity_var.set("")
        messagebox.showinfo("Success", "Task history cleared.")

    def _on_exit(self) -> None:
        """Exit the application."""
        self._root.destroy()

    def _on_load_memory(self) -> None:
        """Load short-term memory from file."""
        try:
            with open(self.paths.memory3, "r", encoding="utf-8") as f:
                data = json.load(f)
            formatted = self._format_memory(data)
            self._memory_text.delete("1.0", tk.END)
            self._memory_text.insert("1.0", formatted)
        except FileNotFoundError:
            self._memory_text.delete("1.0", tk.END)
            self._memory_text.insert("1.0", "No short-term memory found.")

    def _on_save_memory(self) -> None:
        """Save edited short-term memory to file."""
        try:
            raw = self._memory_text.get("1.0", tk.END).strip()
            data = self._parse_memory_text(raw)
            with open(self.paths.memory3, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Success", "Memory saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save memory: {e}")

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _check_similarity(self, task: str) -> None:
        """Check if task is similar to any in history."""
        task_words = set(task.lower().split())
        matches = []
        for history_entry in self._task_history:
            history_words = set(history_entry.lower().split())
            common = task_words & history_words
            for word in common:
                if word in AI2THOR_OBJECTS:
                    matches.append(word)

        if matches:
            self._similarity_var.set("Memory: " + ", ".join(set(matches)))
        else:
            self._similarity_var.set("No similar tasks found.")

    def _load_history(self) -> list:
        try:
            with open(self.paths.task_history, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_history(self) -> None:
        self.paths.history_tasks.mkdir(parents=True, exist_ok=True)
        with open(self.paths.task_history, "w", encoding="utf-8") as f:
            json.dump(self._task_history, f, ensure_ascii=False, indent=4)

    def _populate_history(self) -> None:
        for entry in self._task_history:
            self._history_listbox.insert(tk.END, entry.strip())

    def _save_task_description(self, task: str) -> None:
        self.paths.logs.mkdir(parents=True, exist_ok=True)
        with open(self.paths.task_description, "w", encoding="utf-8") as f:
            json.dump({"task_description": task}, f, indent=2)

    def _save_instruction(self, task: str) -> None:
        content = f"Please help me decompose the following tasks: {task}. Please output only the generated code."
        self.paths.prompts.mkdir(parents=True, exist_ok=True)
        with open(self.paths.prompts / "instruction.txt", "w", encoding="utf-8") as f:
            f.write(content)

    def _save_similarity_flag(self, has_similarity: bool) -> None:
        self.paths.logs.mkdir(parents=True, exist_ok=True)
        with open(self.paths.similarity_flag, "w", encoding="utf-8") as f:
            json.dump({"similarity_flag": has_similarity}, f)

    def _format_memory(self, data: list) -> str:
        lines = []
        for item in data:
            lines.append(f"Object Type: {item.get('objectType', 'N/A')}")
            pos = item.get("position", {})
            lines.append(
                f"Position: x={pos.get('x', 0):.2f}, "
                f"y={pos.get('y', 0):.2f}, z={pos.get('z', 0):.2f}"
            )
            lines.append(f"Object ID: {item.get('objectId', 'N/A')}")
            lines.append("")
        return "\n".join(lines)

    def _parse_memory_text(self, text: str) -> list:
        """Parse the memory text back into structured JSON."""
        lines = text.split("\n")
        items = []
        current = {}
        for line in lines:
            line = line.strip()
            if line.startswith("Object Type: "):
                if current:
                    items.append(current)
                current = {"objectType": line.split("Object Type: ")[1]}
            elif line.startswith("Position: "):
                pos_str = line.split("Position: ")[1]
                parts = dict(p.split("=") for p in pos_str.replace(" ", "").split(","))
                current["position"] = {k: float(v) for k, v in parts.items()}
            elif line.startswith("Object ID: "):
                current["objectId"] = line.split("Object ID: ")[1]
        if current:
            items.append(current)
        return items

    # ─── Run ─────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the Tkinter main loop."""
        self._root.mainloop()
