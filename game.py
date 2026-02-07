from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from data import CARD_INDEX, DECK_P1, DECK_P2


@dataclass
class AnimalInstance:
    instance_id: int
    card_id: str
    owner: int
    hunger: int = 0


@dataclass
class PlantInstance:
    instance_id: int
    card_id: str
    owner: int


@dataclass
class PlayerState:
    name: str
    deck: List[str]
    hand: List[str] = field(default_factory=list)
    pending_control: bool = False


@dataclass
class BiomeState:
    name: str
    cn_base: int
    lmax: int
    cc: int = 0
    cn_temp: int = 0
    cn: int = 0


@dataclass
class GameState:
    players: List[PlayerState]
    biome: BiomeState
    animals: List[AnimalInstance] = field(default_factory=list)
    plants: List[PlantInstance] = field(default_factory=list)
    active_player_index: int = 0
    actions_used: int = 0
    next_instance_id: int = 1
    log: List[str] = field(default_factory=list)
    winner: Optional[str] = None

    def add_log(self, message: str) -> None:
        self.log.append(message)


def start_game() -> GameState:
    deck1 = list(DECK_P1)
    deck2 = list(DECK_P2)
    random.shuffle(deck1)
    random.shuffle(deck2)
    players = [PlayerState(name="Jugador 1", deck=deck1), PlayerState(name="Jugador 2", deck=deck2)]
    biome = BiomeState(name="Bosque", cn_base=4, lmax=6)
    state = GameState(players=players, biome=biome)
    state.add_log("Juego iniciado en el bioma Bosque.")
    start_turn(state)
    return state


def start_turn(state: GameState) -> None:
    player = state.players[state.active_player_index]
    if player.pending_control and check_control(state, player_index=state.active_player_index):
        state.winner = player.name
        state.add_log(f"{player.name} mantiene el control completo y gana la partida.")
        return

    state.actions_used = 0
    biome = state.biome
    biome.cn = biome.cn_base + biome.cn_temp + sum(
        CARD_INDEX[p.card_id]["cnPerTurn"] for p in state.plants
    )
    biome.cn_temp = 0
    state.add_log(
        f"Inicio de turno de {player.name}. CN actual: {biome.cn} (base {biome.cn_base})."
    )
    draw_to_hand(state, player, target_size=8)


def draw_to_hand(state: GameState, player: PlayerState, target_size: int) -> None:
    while len(player.hand) < target_size and player.deck:
        player.hand.append(player.deck.pop(0))
    state.add_log(f"{player.name} roba hasta {len(player.hand)} cartas en mano.")


def play_card(state: GameState, card_id: str) -> bool:
    if state.winner:
        state.add_log("La partida ya terminó.")
        return False
    player = state.players[state.active_player_index]
    if card_id not in player.hand:
        state.add_log("Esa carta no está en la mano.")
        return False
    if state.actions_used >= 3:
        state.add_log("Ya usaste las 3 acciones del turno.")
        return False

    card = CARD_INDEX[card_id]
    if card["kind"] == "plant":
        plant = PlantInstance(
            instance_id=state.next_instance_id, card_id=card_id, owner=state.active_player_index
        )
        state.next_instance_id += 1
        state.plants.append(plant)
        player.hand.remove(card_id)
        state.actions_used += 1
        state.add_log(f"{player.name} juega planta {card['name']}.")
        return True

    if card["kind"] == "animal":
        if not can_play_animal(state, card):
            return False
        animal = AnimalInstance(
            instance_id=state.next_instance_id, card_id=card_id, owner=state.active_player_index
        )
        state.next_instance_id += 1
        state.animals.append(animal)
        player.hand.remove(card_id)
        state.actions_used += 1
        state.add_log(f"{player.name} juega animal {card['name']} (nivel {card['level']}).")
        return True

    state.add_log("Tipo de carta desconocido.")
    return False


def can_play_animal(state: GameState, card: Dict) -> bool:
    biome_cn = state.biome.cn
    animal_type = card["type"]
    level = card["level"]
    has_prey = bool(find_viable_prey(state, predator_level=level))

    if animal_type == "Herbivore":
        if biome_cn >= level:
            return True
        state.add_log("No hay CN suficiente para desplegar herbívoro.")
        return False

    if animal_type == "Carnivore":
        if has_prey:
            return True
        state.add_log("No hay presas viables para desplegar carnívoro.")
        return False

    if animal_type == "Omnivore":
        if biome_cn >= level or has_prey:
            return True
        state.add_log("Omnívoro requiere CN suficiente o presa viable.")
        return False

    state.add_log("Tipo de animal inválido.")
    return False


def find_viable_prey(state: GameState, predator_level: int) -> List[AnimalInstance]:
    threshold = math.ceil(predator_level / 2)
    prey_list = []
    for animal in state.animals:
        card = CARD_INDEX[animal.card_id]
        if card["type"] in {"Herbivore", "Omnivore"} and card["level"] >= threshold:
            prey_list.append(animal)
    return prey_list


def end_turn(state: GameState, hunting_choices: Optional[Dict[int, int]] = None) -> None:
    if state.winner:
        return
    hunting_choices = hunting_choices or {}
    fed_predators = resolve_hunting(state, hunting_choices)
    resolve_feeding(state, fed_predators)
    resolve_starvation(state)
    resolve_conversion(state)
    active_player = state.players[state.active_player_index]
    if check_control(state, state.active_player_index):
        active_player.pending_control = True
        state.add_log(f"{active_player.name} logra amenaza de control.")
    else:
        active_player.pending_control = False
    state.active_player_index = (state.active_player_index + 1) % len(state.players)
    start_turn(state)


def resolve_hunting(state: GameState, hunting_choices: Dict[int, int]) -> set[int]:
    fed_predators: set[int] = set()
    predators = [
        animal
        for animal in state.animals
        if CARD_INDEX[animal.card_id]["type"] in {"Carnivore", "Omnivore"} and animal.hunger >= 1
    ]
    if not predators:
        state.add_log("No hay depredadores con hambre para cazar.")
        return fed_predators
    state.add_log("Fase de caza iniciada.")
    for predator in predators:
        predator_card = CARD_INDEX[predator.card_id]
        prey_id = hunting_choices.get(predator.instance_id)
        if not prey_id:
            state.add_log(f"{predator_card['name']} no tiene objetivo de caza.")
            continue
        prey = next((a for a in state.animals if a.instance_id == prey_id), None)
        if not prey:
            state.add_log(f"Objetivo inválido para {predator_card['name']}.")
            continue
        if not is_viable_prey(predator_card["level"], prey):
            state.add_log(f"{predator_card['name']} no puede cazar esa presa.")
            continue
        if resolve_single_hunt(state, predator, prey):
            fed_predators.add(predator.instance_id)
    return fed_predators


def is_viable_prey(predator_level: int, prey: AnimalInstance) -> bool:
    threshold = math.ceil(predator_level / 2)
    prey_card = CARD_INDEX[prey.card_id]
    return prey_card["type"] in {"Herbivore", "Omnivore"} and prey_card["level"] >= threshold


def resolve_single_hunt(state: GameState, predator: AnimalInstance, prey: AnimalInstance) -> bool:
    predator_card = CARD_INDEX[predator.card_id]
    prey_card = CARD_INDEX[prey.card_id]
    if predator_card["instinct"] >= prey_card["instinct"]:
        state.add_log(f"Instinto favorece a {predator_card['name']}. Combate directo.")
    else:
        if predator_card["mobility"] < prey_card["mobility"]:
            state.add_log(f"{prey_card['name']} escapa por movilidad superior.")
            return False
        state.add_log(f"{predator_card['name']} alcanza a {prey_card['name']} en movilidad.")

    predator_weight_scaled = min(100, int(predator_card["weightKg"] / 10))
    prey_weight_scaled = min(100, int(prey_card["weightKg"] / 10))
    attack_score = predator_card["attack"] + int(0.20 * predator_weight_scaled)
    defense_score = prey_card["defense"] + int(0.25 * prey_weight_scaled)
    if attack_score >= defense_score:
        state.add_log(f"{predator_card['name']} elimina a {prey_card['name']}.")
        state.animals = [a for a in state.animals if a.instance_id != prey.instance_id]
        state.biome.cc += prey_card["level"]
        if prey_card["level"] == predator_card["level"]:
            predator.hunger = 0
        else:
            predator.hunger = max(predator.hunger - 1, 0)
        return True
    else:
        state.add_log(f"{prey_card['name']} resiste el combate contra {predator_card['name']}.")
        return False


def resolve_feeding(state: GameState, fed_predators: set[int]) -> None:
    state.add_log("Fase de alimentación de CN.")
    biome = state.biome
    for level in range(1, biome.lmax + 1):
        level_animals = [
            animal
            for animal in state.animals
            if CARD_INDEX[animal.card_id]["type"] in {"Herbivore", "Omnivore"}
            and CARD_INDEX[animal.card_id]["level"] == level
        ]
        if not level_animals:
            continue
        total_needed = level * len(level_animals)
        if biome.cn >= total_needed:
            biome.cn -= total_needed
            for animal in level_animals:
                animal.hunger = 0
            state.add_log(f"Nivel {level}: todos comen. CN restante {biome.cn}.")
            continue

        state.add_log(
            f"Nivel {level}: CN insuficiente ({biome.cn} disponible) para {len(level_animals)}.")
        duel_candidates = sorted(
            level_animals, key=lambda a: CARD_INDEX[a.card_id]["weightKg"], reverse=True
        )
        if len(duel_candidates) >= 2 and biome.cn >= level:
            winner = duel_candidates[0]
            loser = duel_candidates[1]
            biome.cn -= level
            winner.hunger = 0
            loser.hunger += 1
            state.add_log(
                f"Duelo ecológico: gana {CARD_INDEX[winner.card_id]['name']} y come." \
                f" Pierde {CARD_INDEX[loser.card_id]['name']}."
            )
            for animal in level_animals:
                if animal.instance_id not in {winner.instance_id, loser.instance_id}:
                    animal.hunger += 1
        else:
            for animal in level_animals:
                animal.hunger += 1
            state.add_log("No hay CN suficiente para duelo: todos aumentan hambre.")

    unfed_carnivores = [
        animal
        for animal in state.animals
        if CARD_INDEX[animal.card_id]["type"] == "Carnivore"
        and animal.instance_id not in fed_predators
    ]
    if unfed_carnivores:
        for animal in unfed_carnivores:
            animal.hunger += 1
        state.add_log("Carnívoros sin presa aumentan hambre.")


def resolve_starvation(state: GameState) -> None:
    dead = []
    for animal in state.animals:
        if animal.hunger >= 2:
            dead.append(animal)
    if dead:
        for animal in dead:
            card = CARD_INDEX[animal.card_id]
            state.biome.cc += card["level"]
            state.add_log(f"{card['name']} muere por hambre.")
        state.animals = [a for a in state.animals if a not in dead]
    else:
        state.add_log("No hay muertes por hambre.")


def resolve_conversion(state: GameState) -> None:
    state.biome.cn_temp = math.floor(0.40 * state.biome.cc)
    state.add_log(f"Conversión: CN_temp pasa a {state.biome.cn_temp}.")
    state.biome.cc = 0


def check_control(state: GameState, player_index: int) -> bool:
    biome = state.biome
    for level in range(1, biome.lmax + 1):
        has_level = any(
            CARD_INDEX[animal.card_id]["level"] == level and animal.owner == player_index
            for animal in state.animals
        )
        if not has_level:
            return False
    return True


def get_display_animals_by_level(state: GameState) -> Dict[int, List[AnimalInstance]]:
    grouped: Dict[int, List[AnimalInstance]] = {level: [] for level in range(1, state.biome.lmax + 1)}
    for animal in state.animals:
        level = CARD_INDEX[animal.card_id]["level"]
        grouped[level].append(animal)
    return grouped
