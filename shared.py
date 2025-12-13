# 文件名: shared.py
from scripts.game_state import GameState

#在这里实例化，且全宇宙只实例化这一次
#所有其他文件都要从这里 import GAME
GAME = GameState()