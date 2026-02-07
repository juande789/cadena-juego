import tkinter as tk
from tkinter import ttk

from data import CARD_INDEX
from game import (
    GameState,
    end_turn,
    get_display_animals_by_level,
    play_card,
    start_game,
)


class AnimalDominionUI:
    def __init__(self, root: tk.Tk, state: GameState) -> None:
        self.root = root
        self.state = state
        self.root.title("Animal Dominion - MVP")

        self.biome_vars = {
            "cn": tk.StringVar(),
            "cn_base": tk.StringVar(),
            "cn_temp": tk.StringVar(),
            "cc": tk.StringVar(),
            "lmax": tk.StringVar(),
        }
        self.actions_var = tk.StringVar()
        self.active_player_var = tk.StringVar()

        self.hand_frame = ttk.Frame(self.root)
        self.log_text = None

        self._build_layout()
        self.refresh_ui()

    def _build_layout(self) -> None:
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        biome_frame = ttk.LabelFrame(main_frame, text="Bioma")
        biome_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        for idx, (label, key) in enumerate(
            [
                ("CN actual", "cn"),
                ("CN base", "cn_base"),
                ("CN temp", "cn_temp"),
                ("CC", "cc"),
                ("Lmax", "lmax"),
            ]
        ):
            ttk.Label(biome_frame, text=f"{label}:").grid(row=idx, column=0, sticky="w")
            ttk.Label(biome_frame, textvariable=self.biome_vars[key]).grid(
                row=idx, column=1, sticky="w"
            )

        table_frame = ttk.LabelFrame(main_frame, text="Mesa")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        table_frame.columnconfigure(0, weight=1)
        table_frame.columnconfigure(1, weight=1)

        plants_frame = ttk.LabelFrame(table_frame, text="Plantas en mesa")
        plants_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.plants_list = tk.Listbox(plants_frame, height=6)
        self.plants_list.pack(fill="both", expand=True)

        animals_frame = ttk.LabelFrame(table_frame, text="Animales por nivel")
        animals_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.animals_list = tk.Listbox(animals_frame, height=12)
        self.animals_list.pack(fill="both", expand=True)

        player_frame = ttk.LabelFrame(main_frame, text="Jugador activo")
        player_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        ttk.Label(player_frame, textvariable=self.active_player_var).pack(anchor="w")
        ttk.Label(player_frame, textvariable=self.actions_var).pack(anchor="w")
        self.hand_frame = ttk.Frame(player_frame)
        self.hand_frame.pack(fill="x", pady=5)

        self.end_turn_button = ttk.Button(
            player_frame, text="End Turn", command=self.on_end_turn
        )
        self.end_turn_button.pack(fill="x", pady=5)

        log_frame = ttk.LabelFrame(main_frame, text="Game Log")
        log_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=15, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def refresh_ui(self) -> None:
        biome = self.state.biome
        self.biome_vars["cn"].set(str(biome.cn))
        self.biome_vars["cn_base"].set(str(biome.cn_base))
        self.biome_vars["cn_temp"].set(str(biome.cn_temp))
        self.biome_vars["cc"].set(str(biome.cc))
        self.biome_vars["lmax"].set(str(biome.lmax))

        active_player = self.state.players[self.state.active_player_index]
        self.active_player_var.set(f"Turno de {active_player.name}")
        self.actions_var.set(f"Acciones usadas: {self.state.actions_used} / 3")

        self.plants_list.delete(0, tk.END)
        for plant in self.state.plants:
            card = CARD_INDEX[plant.card_id]
            owner = self.state.players[plant.owner].name
            self.plants_list.insert(
                tk.END, f"{card['name']} (+{card['cnPerTurn']} CN) - {owner}"
            )

        self.animals_list.delete(0, tk.END)
        grouped = get_display_animals_by_level(self.state)
        for level in range(1, self.state.biome.lmax + 1):
            animals = grouped[level]
            if not animals:
                continue
            self.animals_list.insert(tk.END, f"Nivel {level}:")
            for animal in animals:
                card = CARD_INDEX[animal.card_id]
                owner = self.state.players[animal.owner].name
                self.animals_list.insert(
                    tk.END,
                    f"  {card['name']} ({card['type']}) - {owner} | hambre {animal.hunger} | kg {card['weightKg']}",
                )

        for widget in self.hand_frame.winfo_children():
            widget.destroy()
        for card_id in active_player.hand:
            card = CARD_INDEX[card_id]
            btn = ttk.Button(
                self.hand_frame,
                text=f"{card['name']} ({card_id})",
                command=lambda cid=card_id: self.on_play_card(cid),
            )
            btn.pack(side="left", padx=2, pady=2)

        self._refresh_log()
        if self.state.winner:
            self.end_turn_button.configure(state="disabled")
            for widget in self.hand_frame.winfo_children():
                widget.configure(state="disabled")

    def _refresh_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        for line in self.state.log:
            self.log_text.insert(tk.END, line + "\n")
        self.log_text.configure(state="disabled")
        self.log_text.see(tk.END)

    def on_play_card(self, card_id: str) -> None:
        play_card(self.state, card_id)
        self.refresh_ui()

    def on_end_turn(self) -> None:
        if self.state.winner:
            return
        predators = [
            animal
            for animal in self.state.animals
            if CARD_INDEX[animal.card_id]["type"] in {"Carnivore", "Omnivore"}
            and animal.hunger >= 1
        ]
        if not predators:
            end_turn(self.state, {})
            self.refresh_ui()
            return

        self.open_hunting_dialog(predators)

    def open_hunting_dialog(self, predators) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Selección de caza")
        dialog.grab_set()
        selections = {}

        row = 0
        for predator in predators:
            predator_card = CARD_INDEX[predator.card_id]
            ttk.Label(
                dialog,
                text=f"{predator_card['name']} (hambre {predator.hunger}) objetivo:",
            ).grid(row=row, column=0, sticky="w", padx=5, pady=5)
            prey_options = self._get_prey_options(predator_card["level"])
            var = tk.StringVar(value="(Omitir)")
            menu = ttk.OptionMenu(dialog, var, var.get(), *prey_options)
            menu.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
            selections[predator.instance_id] = var
            row += 1

        def confirm() -> None:
            choices = {}
            for predator_id, var in selections.items():
                selection = var.get()
                if selection == "(Omitir)":
                    continue
                prey_id = int(selection.split("#")[-1])
                choices[predator_id] = prey_id
            end_turn(self.state, choices)
            dialog.destroy()
            self.refresh_ui()

        ttk.Button(dialog, text="Confirmar", command=confirm).grid(
            row=row, column=0, columnspan=2, pady=10
        )

    def _get_prey_options(self, predator_level: int):
        options = ["(Omitir)"]
        threshold = (predator_level + 1) // 2
        for animal in self.state.animals:
            card = CARD_INDEX[animal.card_id]
            if card["type"] in {"Herbivore", "Omnivore"} and card["level"] >= threshold:
                owner = self.state.players[animal.owner].name
                options.append(
                    f"{card['name']} (N{card['level']}) - {owner} #{animal.instance_id}"
                )
        return options


def main() -> None:
    root = tk.Tk()
    state = start_game()
    AnimalDominionUI(root, state)
    root.mainloop()


if __name__ == "__main__":
    main()
