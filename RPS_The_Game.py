import cv2
import mediapipe as mp
import numpy as np
import time
import math
import random
import sys
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide" #blocking pygame import message
import pygame
from mediapipe.python.solutions import hands as mp_hands
from mediapipe.python.solutions import drawing_utils as mp_drawing

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class RPS_OpenCV():
    def __init__(self):
        self.Win_phrases = ["Keep it up!", "You're doing great!", "Should be easy for you...", "Great read!"]
        self.Lose_phrases = ["Don't give up!", "Better luck next time!", "Don't lose hope!", "Opponent got lucky..."]
        self.Draw_phrases = ["What a tough fight!", "It was close...", "Great minds think alike!"]
        self.Winner_text = ""
        self.Round_end_phrase = ""

        self.CHOOSING_ROUNDS_allowed_gestures = ["One", "Scissor", "Three", "Four", "Paper", "Stop"]
        self.PLAYING_allowed_gestures = ["Rock", "Paper", "Scissor", "Stop"]

        self.Bot_state = "Smile"
        self.Bot_Hand_state_name = "Waiting..."

        self.RPS_list = ["Rock", "Paper", "Scissor"]
        self.Player_selection = ""
        self.Bot_selection = ""
        self.Winner = ""

        self.Current_round = 1
        self.Total_rounds = 10
        self.Bot_score = 0
        self.Player_score = 0
        
        self.switch_camera_previous_time = time.time()
        self.switch_camera_cooldown = 3
        self.camera_list_index = 0
        self.Camera_width = 640
        self.Camera_height = 480

        self.Score_given = False
        self.Last_selectoin_index = None

        self.Quit_game = False
        self.Last_frames_game_state = ""
        self.Game_state = "TUTORIAL"
        self.Background_music_started = False

        self.Previous_time = time.time()
        self.Time_countdown_TUTORIAL = 5
        self.Time_countdown_CHOOSING_ROUNDS = 5
        self.Time_countdown_PLAYING = 5
        self.Time_countdown_ROUND_END = 5
        self.Time_countdown_GAME_END = 5

        self.key_pressed = False

        self.FPS_previous_time = time.time()

        self.Circule_A_C_gap = 30 #Arrow and Center gap
        self.Circule_A_B_gap = 30 #Arrow and Border gap
        self.Circule_Border_thickness = 25
        self.Circule_Arrow_Length = 160
        self.Transition_phase = 0
        self.Transition_loop_counter = 1
        self.Transition_sfx_played = False
        self.Transition_next_game_state = ""
        self.Previous_time_transition = 0.0
        self.Did_transition_timer_set = False
        self.Time_stop = False

    # GUI & GAME
    def CHOOSING_ROUNDS_display_selector(self):
        X_gaps = 570
        Y_gaps = 200
        selection_index = self.CHOOSING_ROUNDS_allowed_gestures.index(f"{self.Hand_state_name}")
        if self.Last_selectoin_index != selection_index:
            self.Selection_sfx.play()
            self.Last_selectoin_index = selection_index
        Y_order , X_order = divmod(selection_index, 2)

        #---------- CURSOR ----------
        first_selector_X_coords = [30, 89, 30]
        first_selector_Y_coords = [550, 587, 624]

        selector_X_coords = [coord + X_order*X_gaps for coord in first_selector_X_coords]
        selector_Y_coords = [coord + Y_order*Y_gaps for coord in first_selector_Y_coords]
        triangle_points = np.array([(x, y) for x, y in zip(selector_X_coords, selector_Y_coords)], np.int32)

        cv2.fillConvexPoly(self.master_canvas, triangle_points, (0,255,0), cv2.LINE_AA)
        cv2.polylines(self.master_canvas, [triangle_points], True, (0, 255, 0), 2, lineType=cv2.LINE_AA)

        #---------- BORDER ----------
        first_border_top_left_coords = (116, 526)
        first_border_bottom_right_coords = (554, 648)
        first_line_top_coords = (432, 526)
        first_line_bottom_coords = (432, 648)

        border_top_left_coords = (first_border_top_left_coords[0] + X_order*X_gaps, first_border_top_left_coords[1] + Y_order*Y_gaps)
        border_bottom_right_coords = (first_border_bottom_right_coords[0] + X_order*X_gaps, first_border_bottom_right_coords[1] + Y_order*Y_gaps)
        line_top_coords = (first_line_top_coords[0] + X_order*X_gaps, first_line_top_coords[1] + Y_order*Y_gaps)
        line_bottom_coords = (first_line_bottom_coords[0] + X_order*X_gaps, first_line_bottom_coords[1] + Y_order*Y_gaps)

        cv2.rectangle(self.master_canvas, border_top_left_coords, border_bottom_right_coords, (0,255,0), 3)
        cv2.line(self.master_canvas, line_top_coords, line_bottom_coords, (0,255,0), 3)

    def CHOOSING_ROUNDS_set_total_rounds(self, Hand_state_name):
        if Hand_state_name == "One": self.Total_rounds = 1
        elif Hand_state_name == "Scissor": self.Total_rounds = 3
        elif Hand_state_name == "Three": self.Total_rounds = 5
        elif Hand_state_name == "Four": self.Total_rounds = 10
        elif Hand_state_name == "Paper": self.Total_rounds = 99999999
        elif Hand_state_name == "Stop":  self.Quit_game = True

    def PLAYING_ROUND_END_display_bot_face(self, Bot_state): #Bot_state= "Smile" or "Won" or "Lost" or "Draw"
        if Bot_state == "Smile": self.master_canvas[150:630, 100:740] = self.Image_Dict["Bot_smile_img"].copy()
        elif Bot_state == "Won": self.master_canvas[150:630, 100:740] = self.Image_Dict["Bot_won_img"].copy()
        elif Bot_state == "Lost": self.master_canvas[150:630, 100:740] = self.Image_Dict["Bot_lost_img"].copy()
        elif Bot_state == "Draw": self.master_canvas[150:630, 100:740] = self.Image_Dict["Bot_draw_img"].copy()
        cv2.rectangle(self.master_canvas, (100,150), (740,630), (0,0,255), 3)
    
    def PLAYING_ROUND_END_display_hand_img(self, Hand_state_name, whose): #whose= "Bot" or "Player"
        if whose == "Bot": #Don't need to add Allowed Gestures 
            text_size = cv2.getTextSize(f"State: {Hand_state_name}", cv2.FONT_HERSHEY_PLAIN, 2.5, 2)
            Text_x_coord = int(240+(360-text_size[0][0])/2)
            cv2.putText(self.master_canvas, f"State: {Hand_state_name}", (Text_x_coord,710), cv2.FONT_HERSHEY_PLAIN, 2.5, (0,0,255), 3)

            self.master_canvas[730:1030, 270:570] = self.Image_Dict[f"{Hand_state_name}_img_small"].copy()
            cv2.rectangle(self.master_canvas, (270,730), (570,1030), (0,0,255), 3)

        elif whose == "Player":
            if Hand_state_name not in self.PLAYING_allowed_gestures:
                Hand_state_name = "Waiting..."

            text_size = cv2.getTextSize(f"State: {Hand_state_name}", cv2.FONT_HERSHEY_PLAIN, 2.5, 2)
            Text_x_coord = int(1320+(360-text_size[0][0])/2)
            cv2.putText(self.master_canvas, f"State: {Hand_state_name}", (Text_x_coord,710), cv2.FONT_HERSHEY_PLAIN, 2.5, (255,0,0), 3)

            self.master_canvas[730:1030, 1350:1650] = self.Image_Dict[f"{Hand_state_name}_img_small"].copy()
            cv2.rectangle(self.master_canvas, (1350,730), (1650,1030), (255,0,0), 3)
    
    def ROUND_END_choose_winner(self, Bot_selection, Player_selection):
        Bot_selection_index = self.RPS_list.index(Bot_selection)
        Player_selection_index = self.RPS_list.index(Player_selection)
        index_diff = Player_selection_index - Bot_selection_index
        if index_diff == 0: self.Winner = "Nobody"
        elif index_diff == 1 or index_diff == -2: self.Winner = "Player"
        elif index_diff == 2 or index_diff == -1: self.Winner = "Bot"

    def ROUND_END_display_winner_text(self):
        if self.Winner_text == "":
            if self.Winner == "Player":
                self.Winner_text = "PLAYER WON THE ROUND!"
                self.Round_end_phrase = random.choice(self.Win_phrases)
            elif self.Winner == "Bot":
                self.Winner_text = "OPPONENT WON THE ROUND!"
                self.Round_end_phrase = random.choice(self.Lose_phrases)
            elif self.Winner == "Nobody":
                self.Winner_text = "NOBODY WON THE ROUND!"
                self.Round_end_phrase = random.choice(self.Draw_phrases)
        
        Winner_text_size = cv2.getTextSize(self.Winner_text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)
        cv2.putText(self.master_canvas, self.Winner_text, (960-int(Winner_text_size[0][0]/2), 775+int(Winner_text_size[0][1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 1.2,(0,0,0), 3)

        Phrase_text_size = cv2.getTextSize(self.Round_end_phrase, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
        cv2.putText(self.master_canvas, self.Round_end_phrase, (960-int(Phrase_text_size[0][0]/2), 830+int(Phrase_text_size[0][1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,0), 2)

        Countdown_text = f"Continuing on to the next round in {self.Time_countdown_ROUND_END} seconds..."
        Countdown_text_size = cv2.getTextSize(Countdown_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
        cv2.putText(self.master_canvas, Countdown_text, (960-int(Countdown_text_size[0][0]/2) , 910-int(Countdown_text_size[0][1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)

    def ROUND_END_display_score_table(self):
        if not self.Score_given:
            if not self.Winner == "Nobody": self.Current_round += 1
            if self.Winner == "Player": self.Player_score += 1
            elif self.Winner == "Bot": self.Bot_score += 1
            self.Score_given = True

        Bot_score_text_lenght = cv2.getTextSize(f"{self.Bot_score}", cv2.FONT_HERSHEY_PLAIN, 4, 5)[0][0]
        Player_score_text_lenght = cv2.getTextSize(f"{self.Player_score}", cv2.FONT_HERSHEY_PLAIN, 4, 5)[0][0]
        cv2.putText(self.master_canvas, f"{self.Bot_score}", (int(868-Bot_score_text_lenght/2), 248), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255), 5)
        cv2.putText(self.master_canvas, f"{self.Player_score}", (int(1057-Player_score_text_lenght/2), 248), cv2.FONT_HERSHEY_PLAIN, 4, (255,0,0), 5)

    def ROUND_END_set_icons_bot_state(self, Winner):
        if Winner == "Nobody":
            self.Bot_state = "Draw"
            icon_1 = "icon_Sword_red"
            icon_2 = "icon_Shield_red"
            icon_3 = "icon_Shield_blue"
            icon_4 = "icon_Sword_blue"

        elif Winner == "Player":
            self.Bot_state = "Lost"
            icon_1 = "icon_Moai_img"
            icon_2 = "icon_Moai_img"
            icon_3 = "icon_Crown_img"
            icon_4 = "icon_Crown_img"

        elif Winner == "Bot":
            self.Bot_state = "Won"
            icon_1 = "icon_Crown_img"
            icon_2 = "icon_Crown_img"
            icon_3 = "icon_Moai_img"
            icon_4 = "icon_Moai_img"
        
        return self.Bot_state, icon_1, icon_2, icon_3, icon_4

    def ROUND_END_play_sfx(self):
        if not self.ROUND_END_sfx_played:
            if self.Winner == "Nobody":
                self.Draw_sword_sfx.play()
            else:
                if self.Winner == "Player": winning_hand = self.Player_selection
                else: winning_hand = self.Bot_selection
                getattr(self, f"{winning_hand}_sfx").play()
            self.ROUND_END_sfx_played = True

    def ROUND_GAME_END_display_icons(self, icon_1, icon_2, icon_3, icon_4):
        if not icon_1 == None: self.master_canvas[53:146, 103:196] = self.Image_Dict[icon_1].copy()
        if not icon_2 == None: self.master_canvas[53:146, 643:736] = self.Image_Dict[icon_2].copy()
        if not icon_3 == None: self.master_canvas[53:146, 1183:1276] = self.Image_Dict[icon_3].copy()
        if not icon_4 == None: self.master_canvas[53:146, 1723:1816] = self.Image_Dict[icon_4].copy()

    def GAME_END_display_loadout_icons(self, Winner):
        if Winner == "Nobody":
            cv2.rectangle(self.master_canvas, (1180,50), (1819,149), (255,255,255), -1)
            cv2.rectangle(self.master_canvas, (1180,50), (1819,149), (255,0,0), 3)
            cv2.line(self.master_canvas, (1279,50), (1279,149), (255,0,0), 3)
            cv2.line(self.master_canvas, (1720,50), (1720,149), (255,0,0), 3)
            Player_text_size = cv2.getTextSize("Player", cv2.FONT_HERSHEY_SIMPLEX, 2.75, 5)[0]
            cv2.putText(self.master_canvas, "Player", (1500-int(Player_text_size[0]/2), 92+int(Player_text_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 2.75, (255,0,0), 5)

            cv2.rectangle(self.master_canvas, (100,50), (739,149), (255,255,255), -1)
            cv2.rectangle(self.master_canvas, (100,50), (739,149), (0,0,255), 3)
            cv2.line(self.master_canvas, (199,50), (199,149), (0,0,255), 3)
            cv2.line(self.master_canvas, (640,50), (640,149), (0,0,255), 3)
            Opponent_text_size = cv2.getTextSize("Opponent", cv2.FONT_HERSHEY_SIMPLEX, 2.75, 5)[0]
            cv2.putText(self.master_canvas, "Opponent", (420-int(Opponent_text_size[0]/2), 92+int(Opponent_text_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 2.75, (0,0,255), 5)

            self.ROUND_GAME_END_display_icons("icon_Sword_red", "icon_Shield_red", "icon_Shield_blue", "icon_Sword_blue")

        elif Winner == "Player":
            cv2.rectangle(self.master_canvas, (1180,50), (1819,149), (255,255,255), -1)
            cv2.rectangle(self.master_canvas, (1180,50), (1819,149), (255,0,0), 3)
            cv2.line(self.master_canvas, (1279,50), (1279,149), (255,0,0), 3)
            cv2.line(self.master_canvas, (1720,50), (1720,149), (255,0,0), 3)
            Player_text_size = cv2.getTextSize("Player", cv2.FONT_HERSHEY_SIMPLEX, 2.75, 5)[0]
            cv2.putText(self.master_canvas, "Player", (1500-int(Player_text_size[0]/2), 92+int(Player_text_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 2.75, (255,0,0), 5)

            cv2.rectangle(self.master_canvas, (180,135), (659,209), (255,255,255), -1)
            cv2.rectangle(self.master_canvas, (180,135), (659,209), (175,175,175), 3)
            cv2.line(self.master_canvas, (254,135), (254,209), (175,175,175), 3)
            cv2.line(self.master_canvas, (585,135), (585,209), (175,175,175), 3)
            Opponent_text_size = cv2.getTextSize("Opponent", cv2.FONT_HERSHEY_SIMPLEX, 2, 3)[0]
            cv2.putText(self.master_canvas, "Opponent", (420-int(Opponent_text_size[0]/2), 165+int(Opponent_text_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 2, (175,175,175), 3)
            
            cv2.rectangle(self.master_canvas, (100,664), (1819,1030), (255,0,0), 5)
            self.ROUND_GAME_END_display_icons(None, None, "icon_Crown_img", "icon_Crown_img")
            self.master_canvas[138:208, 182:252] = self.Image_Dict["icon_Moai_img_small"].copy()
            self.master_canvas[138:208, 587:657] = self.Image_Dict["icon_Moai_img_small"].copy()
            
        elif Winner == "Bot":
            cv2.rectangle(self.master_canvas, (1260,135), (1739,209), (255,255,255), -1)
            cv2.rectangle(self.master_canvas, (1260,135), (1739,209), (175,175,175), 3)
            cv2.line(self.master_canvas, (1334,135), (1334,209), (175,175,175), 3)
            cv2.line(self.master_canvas, (1665,135), (1665,209), (175,175,175), 3)
            Opponent_text_size = cv2.getTextSize("Player", cv2.FONT_HERSHEY_SIMPLEX, 2, 3)[0]
            cv2.putText(self.master_canvas, "Player", (1500-int(Opponent_text_size[0]/2), 165+int(Opponent_text_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 2, (175,175,175), 3)

            cv2.rectangle(self.master_canvas, (100,50), (739,149), (255,255,255), -1)
            cv2.rectangle(self.master_canvas, (100,50), (739,149), (0,0,255), 3)
            cv2.line(self.master_canvas, (199,50), (199,149), (0,0,255), 3)
            cv2.line(self.master_canvas, (640,50), (640,149), (0,0,255), 3)
            Opponent_text_size = cv2.getTextSize("Opponent", cv2.FONT_HERSHEY_SIMPLEX, 2.75, 5)[0]
            cv2.putText(self.master_canvas, "Opponent", (420-int(Opponent_text_size[0]/2), 100+int(Opponent_text_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 2.75, (0,0,255), 5)

            cv2.rectangle(self.master_canvas, (100,664), (1819,1030), (0,0,255), 5)
            self.ROUND_GAME_END_display_icons("icon_Crown_img", "icon_Crown_img", None, None)
            self.master_canvas[138:208, 1262:1332] = self.Image_Dict["icon_Moai_img_small"].copy()
            self.master_canvas[138:208, 1667:1737] = self.Image_Dict["icon_Moai_img_small"].copy()

    def GAME_END_display_text(self, winner):
        if winner == "Nobody":
            winner_text_1_game_end = "DRAW!"
            winner_text_2_game_end = "NOBODY IS THE WINNER OF THE GAME!"
            winner_text_color = (0,0,0)

        elif winner == "Player":
            winner_text_1_game_end = "VICTORY!"
            winner_text_2_game_end = "PLAYER IS THE WINNER OF THE GAME!"
            winner_text_color = (255,0,0)

        elif winner == "Bot":
            winner_text_1_game_end = "DEFEAT!"
            winner_text_2_game_end = "OPPONENT IS THE WINNER OF THE GAME!"
            winner_text_color = (0,0,255)
        
        winner_text_1_size = cv2.getTextSize(winner_text_1_game_end, cv2.FONT_HERSHEY_SIMPLEX, 3.5, 9)[0]
        cv2.putText(self.master_canvas, winner_text_1_game_end, (960-int(winner_text_1_size[0]/2), 740+int(winner_text_1_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 3.5, winner_text_color, 9)

        winner_text_2_size = cv2.getTextSize(winner_text_2_game_end, cv2.FONT_HERSHEY_SIMPLEX, 1.25, 3)[0]
        cv2.putText(self.master_canvas, winner_text_2_game_end, (960-int(winner_text_2_size[0]/2), 865+int(winner_text_2_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 1.25, winner_text_color, 3)

        Countdown_text = f"Returning to the ROUND SELECTION in {self.Time_countdown_GAME_END} seconds..."
        Countdown_text_size = cv2.getTextSize(Countdown_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
        cv2.putText(self.master_canvas, Countdown_text, (960-int(Countdown_text_size[0]/2) , 980+int(Countdown_text_size[1]/2)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,0), 2)

    def GAME_END_display_camera_bot(self):
        if self.Bot_score == self.Player_score:
            Winner = "Nobody"
            self.master_canvas[150:630, 1180:1820] = self.Camera 
            cv2.rectangle(self.master_canvas, (1180,150), (1820,630), (255,0,0), 3)

            self.master_canvas[150:630, 100:740] = self.Image_Dict["Bot_draw_img"].copy()
            cv2.rectangle(self.master_canvas, (100,150), (740,630), (0,0,255), 3)

        elif self.Player_score > self.Bot_score:
            Winner = "Player"
            self.master_canvas[150:630, 1180:1820] = self.Camera
            cv2.rectangle(self.master_canvas, (1180,150), (1820,630), (255,0,0), 3)

            small_bot_face = cv2.resize(self.Image_Dict["Bot_lost_img"], (480,360))
            gray_small_bot_face = cv2.cvtColor(small_bot_face, cv2.COLOR_BGR2GRAY)
            wasted_bot_face = cv2.cvtColor(gray_small_bot_face, cv2.COLOR_GRAY2BGR)
            self.master_canvas[210:570, 180:660] = wasted_bot_face
            cv2.rectangle(self.master_canvas, (180,210), (660,570), (175,175,175), 3)

            self.master_canvas[662:1033, 98:1822] = self.Image_Dict["BG_Game_end_blue_img"].copy()

        elif self.Bot_score > self.Player_score:
            Winner = "Bot"
            small_camera = cv2.resize(self.Camera, (480,360))
            gray_small_camera = cv2.cvtColor(small_camera, cv2.COLOR_BGR2GRAY)
            wasted_camera = cv2.cvtColor(gray_small_camera, cv2.COLOR_GRAY2BGR)
            self.master_canvas[210:570, 1260:1740] = wasted_camera
            cv2.rectangle(self.master_canvas, (1260,210), (1740,570), (175,175,175), 3)

            self.master_canvas[150:630, 100:740] = self.Image_Dict["Bot_won_img"].copy()
            cv2.rectangle(self.master_canvas, (100,150), (740,630), (0,0,255), 3)

            self.master_canvas[662:1033, 98:1822] = self.Image_Dict["BG_Game_end_red_img"].copy()
            
        self.GAME_END_display_loadout_icons(Winner)
        return Winner

    def GAME_END_display_score_table(self):
        Bot_score_text_lenght = cv2.getTextSize(f"{self.Bot_score}", cv2.FONT_HERSHEY_PLAIN, 4, 5)[0][0]
        Player_score_text_lenght = cv2.getTextSize(f"{self.Player_score}", cv2.FONT_HERSHEY_PLAIN, 4, 5)[0][0]
        cv2.putText(self.master_canvas, f"{self.Bot_score}", (int(868-Bot_score_text_lenght/2), 248), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255), 5)
        cv2.putText(self.master_canvas, f"{self.Player_score}", (int(1057-Player_score_text_lenght/2), 248), cv2.FONT_HERSHEY_PLAIN, 4, (255,0,0), 5)

    def TUTORIAL(self):
        self.master_canvas[0:1080, 0:1920] = self.Image_Dict["BG_Tutorial_img"].copy()
        self.master_canvas[28:568, 1172:1892] = self.Camera
        cv2.rectangle(self.master_canvas, (1172,26), (1893,569), (0,255,0), 3)
        self.master_canvas[594:938, 1547:1891] = self.Image_Dict[f"{self.Hand_state_name}_img"].copy()

        if self.Hand_state_name == "OK":
            Current_time = time.time()
            Time_diff = Current_time - self.Previous_time
            if Time_diff > 1:
                self.Time_sound_player()
                if self.Time_countdown_TUTORIAL == 1:
                    self.Start_Transition("CHOOSING_ROUNDS")
                else:
                    self.Time_countdown_TUTORIAL -= 1
                self.Previous_time = Current_time
        else: 
            self.Previous_time = time.time()

        text_size = cv2.getTextSize(f"{self.Time_countdown_TUTORIAL}", cv2.FONT_HERSHEY_DUPLEX, 4, 8)
        cv2.putText(self.master_canvas, f"{self.Time_countdown_TUTORIAL}", (int(1347-text_size[0][0]/2), int(801+text_size[0][1]/2)), cv2.FONT_HERSHEY_DUPLEX, 4, (0,0,0), 8)

    def CHOOSING_ROUNDS(self):
        self.master_canvas[0:1080, 0:1920] = self.Image_Dict["BG_Round_Selection_img"].copy()
        self.master_canvas[28:568, 1172:1892] = self.Camera
        cv2.rectangle(self.master_canvas, (1172,26), (1893,569), (0,0,255), 3)

        if self.Hand_state_name in self.CHOOSING_ROUNDS_allowed_gestures:
            if self.Hand_state_name == "Scissor": self.master_canvas[594:938, 1547:1891] = self.Image_Dict["Two_img"].copy()
            else: self.master_canvas[594:938, 1547:1891] = self.Image_Dict[f"{self.Hand_state_name}_img"].copy()

            self.CHOOSING_ROUNDS_display_selector()

            text_size = cv2.getTextSize(f"{self.Time_countdown_CHOOSING_ROUNDS}", cv2.FONT_HERSHEY_DUPLEX, 4, 8)
            cv2.putText(self.master_canvas, f"{self.Time_countdown_CHOOSING_ROUNDS}", (int(1347-text_size[0][0]/2), int(801+text_size[0][1]/2)), cv2.FONT_HERSHEY_DUPLEX, 4, (0,0,0), 8)

            Current_time = time.time()
            Time_diff = Current_time - self.Previous_time
            if Time_diff > 1:
                self.Time_sound_player()
                if self.Time_countdown_CHOOSING_ROUNDS == 1:
                    self.CHOOSING_ROUNDS_set_total_rounds(self.Hand_state_name)
                    self.Start_Transition("PLAYING")
                else:
                    self.Time_countdown_CHOOSING_ROUNDS -= 1
                self.Previous_time = Current_time
        else:
            text_size = cv2.getTextSize(f"{self.Time_countdown_CHOOSING_ROUNDS}", cv2.FONT_HERSHEY_DUPLEX, 4, 8)
            cv2.putText(self.master_canvas, f"{self.Time_countdown_CHOOSING_ROUNDS}", (int(1347-text_size[0][0]/2), int(801+text_size[0][1]/2)), cv2.FONT_HERSHEY_DUPLEX, 4, (0,0,0), 8)

            self.master_canvas[594:938, 1547:1891] = self.Image_Dict["Waiting..._img"].copy()
            self.Previous_time = time.time()
    
    def PLAYING(self):
        self.master_canvas[0:1080, 0:1920] = self.Image_Dict["BG_Playing_img"].copy()

        if self.Total_rounds>999: round_text = f"Round: {self.Current_round}/ inf"
        else: round_text = f"Round: {self.Current_round}/{self.Total_rounds}"
        round_text_size = cv2.getTextSize(round_text, cv2.FONT_HERSHEY_PLAIN, 2.5, 3)
        cv2.putText(self.master_canvas, round_text, (960-int(round_text_size[0][0]/2), 100+int(round_text_size[0][1]/2)), cv2.FONT_HERSHEY_PLAIN, 2.5, (0,0,0), 3)

        self.PLAYING_ROUND_END_display_hand_img(self.Bot_Hand_state_name, "Bot")
        self.PLAYING_ROUND_END_display_hand_img(self.Hand_state_name, "Player")

        self.master_canvas[150:630, 1180:1820] = self.Camera #Camera
        cv2.rectangle(self.master_canvas, (1180,150), (1820,630), (255,0,0), 3)

        self.PLAYING_ROUND_END_display_bot_face(f"{self.Bot_state}")
    
        cv2.putText(self.master_canvas, f"{self.Time_countdown_PLAYING}", (934,315), cv2.FONT_HERSHEY_PLAIN, 5, (0,0,0), 5)

        if self.Hand_state_name in self.RPS_list or self.Hand_state_name == "Stop":
            Current_time = time.time()
            Time_diff = Current_time - self.Previous_time
            if Time_diff > 1:
                self.Time_sound_player()
                if self.Time_countdown_PLAYING == 1:
                    if self.Hand_state_name == "Stop": 
                        self.Start_Transition("GAME_END")
                    else:
                        self.Bot_selection = random.choice(self.RPS_list) #Rock, Paper, Scissor
                        self.Player_selection = self.Hand_state_name
                        self.Start_Transition("ROUND_END")
                else:
                    self.Time_countdown_PLAYING -= 1
                self.Previous_time = Current_time
        else:
            self.Previous_time = time.time()

        Bot_score_text_lenght = cv2.getTextSize(f"{self.Bot_score}", cv2.FONT_HERSHEY_PLAIN, 4, 5)[0][0]
        Player_score_text_lenght = cv2.getTextSize(f"{self.Player_score}", cv2.FONT_HERSHEY_PLAIN, 4, 5)[0][0]
        cv2.putText(self.master_canvas, f"{self.Bot_score}", (870-int(Bot_score_text_lenght/2), 862), cv2.FONT_HERSHEY_PLAIN, 4, (0,0,255), 5)
        cv2.putText(self.master_canvas, f"{self.Player_score}", (1055-int(Player_score_text_lenght/2), 862), cv2.FONT_HERSHEY_PLAIN, 4, (255,0,0), 5)

    def ROUND_END(self):
        self.master_canvas[0:1080, 0:1920] = self.Image_Dict["BG_Round_end_img"].copy()
        self.master_canvas[150:630, 1180:1820] = self.Camera
        cv2.rectangle(self.master_canvas, (1180,150), (1820,630), (255,0,0), 3)

        self.ROUND_END_choose_winner(self.Bot_selection, self.Player_selection)

        self.Bot_Hand_state_name = self.Bot_selection
        self.PLAYING_ROUND_END_display_hand_img(self.Bot_selection, "Bot")
        self.PLAYING_ROUND_END_display_hand_img(self.Player_selection, "Player")

        self.Bot_state, icon_1, icon_2, icon_3, icon_4 = self.ROUND_END_set_icons_bot_state(self.Winner)
        self.ROUND_GAME_END_display_icons(icon_1, icon_2, icon_3, icon_4)
        self.PLAYING_ROUND_END_display_bot_face(self.Bot_state)

        self.ROUND_END_display_score_table()
        self.ROUND_END_display_winner_text()

        self.ROUND_END_play_sfx()
        
        Current_time = time.time()
        Time_diff = Current_time - self.Previous_time
        if Time_diff > 1:
            if self.Time_countdown_ROUND_END == 1:
                if self.Current_round > self.Total_rounds and not self.Winner == "Nobody":
                    self.Start_Transition("GAME_END")
                else:
                    self.Start_Transition("PLAYING")
            else:
                self.Time_countdown_ROUND_END -= 1
            self.Previous_time = Current_time

    def GAME_END(self):
        self.master_canvas[0:1080, 0:1920] = self.Image_Dict["BG_Game_end_img"].copy()
        winner = self.GAME_END_display_camera_bot()
        self.GAME_END_display_score_table()
        self.GAME_END_display_text(winner)
        if not self.GAME_END_sfx_played:
            if winner == "Nobody" : self.Trumpet_draw_sfx.play()
            elif winner == "Player" : self.Trumpet_won_sfx.play()
            elif winner == "Bot" : self.Trumpet_lost_sfx.play()
            self.GAME_END_sfx_played = True

        Current_time = time.time()
        Time_diff = Current_time - self.Previous_time
        if Time_diff > 1:
            if self.Time_countdown_GAME_END == 1:
                self.Start_Transition("CHOOSING_ROUNDS")
            else:
                self.Time_countdown_GAME_END -= 1
            self.Previous_time = Current_time

    # MEDIAPIPE & HAND RECOGNITION
    def Calculate_degree(self, x1, y1, x2, y2):
        delta_x , delta_y = x1-x2 , y1-y2
        try:
            angle_deg = math.degrees(math.atan2(delta_y,delta_x))
        except ZeroDivisionError:
            if delta_y > 0: angle_deg = 90
            else: angle_deg = 270
        return angle_deg

    def Get_hand_rotation(self, Lm_coords):
        abs_x_diff_5_17 = abs(Lm_coords[5][0] - Lm_coords[17][0])
        abs_y_diff_5_17 = abs(Lm_coords[5][1] - Lm_coords[17][1])
        if abs_x_diff_5_17 >= abs_y_diff_5_17: Hand_rotation = "Horizontal"
        else: Hand_rotation = "Vertical"
        return Hand_rotation

    def Get_finger_states(self, Hand_type, Hand_rotation, Lm_coords): # + , TRUE = open,  - , FALSE = close
        if Hand_rotation == "Horizontal":
            index_finger = Lm_coords[6][1] - Lm_coords[8][1]
            middle_finger = Lm_coords[10][1] - Lm_coords[12][1]
            ring_finger = Lm_coords[14][1] - Lm_coords[16][1]
            pinky_finger = Lm_coords[18][1] - Lm_coords[20][1]
            if Hand_type == "Right": thumb_finger = Lm_coords[2][0] - Lm_coords[4][0]
            elif Hand_type == "Left": thumb_finger = Lm_coords[4][0] - Lm_coords[2][0]

        elif Hand_rotation == "Vertical":
            if Hand_type == "Right": 
                thumb_finger = Lm_coords[2][1] - Lm_coords[4][1]
                index_finger = Lm_coords[6][0] - Lm_coords[8][0]
                middle_finger = Lm_coords[10][0] - Lm_coords[12][0]
                ring_finger = Lm_coords[14][0] - Lm_coords[16][0]
                pinky_finger = Lm_coords[18][0] - Lm_coords[20][0]
            elif Hand_type == "Left":
                thumb_finger = Lm_coords[2][1] - Lm_coords[4][1]
                index_finger = -(Lm_coords[6][0] - Lm_coords[8][0])
                middle_finger = -(Lm_coords[10][0] - Lm_coords[12][0])
                ring_finger = -(Lm_coords[14][0] - Lm_coords[16][0])
                pinky_finger = -(Lm_coords[18][0] - Lm_coords[20][0])

        Finger_list = [thumb_finger, index_finger, middle_finger, ring_finger, pinky_finger]
        Finger_data = {}
        for id, value in enumerate(Finger_list):
            if value < 0: Finger_data[id] = False
            else: Finger_data[id] = True
        return Finger_data

    def Chooseing_hand_state(self, Finger_data): #True = finger is opened // False = finger is closed
        Hand_state_name = "Waiting..."
        four_finger = [Finger_data[1], Finger_data[2], Finger_data[3], Finger_data[4]] #fingers except thumb

        if Finger_data[0] == True:
            if all(four_finger): Hand_state_name = "Paper"
            elif not any(four_finger): Hand_state_name = "OK"

        elif Finger_data[0] == False:
            if four_finger == [False, False, False, False]: Hand_state_name = "Rock"
            elif four_finger == [True, False, False, False]: Hand_state_name = "One"
            elif four_finger == [True, True, False, False]: Hand_state_name = "Scissor"
            elif four_finger == [True, True, True, False]: Hand_state_name = "Three"
            elif four_finger == [True, True, True, True]: Hand_state_name = "Four"
            
        return Hand_state_name

    def Get_player_hand_state(self, Right_lm_coords, Left_lm_coords):
        if Right_lm_coords:
            Hand_rotation = self.Get_hand_rotation(Right_lm_coords)
            Finger_data = self.Get_finger_states("Right", Hand_rotation, Right_lm_coords)

            degree_0_9 = self.Calculate_degree(Right_lm_coords[0][0], Right_lm_coords[0][1], Right_lm_coords[9][0], Right_lm_coords[9][1])
            degree_9_12 = self.Calculate_degree(Right_lm_coords[9][0], Right_lm_coords[9][1], Right_lm_coords[12][0], Right_lm_coords[12][1])
            
            if 60<degree_0_9<100 and -15<degree_9_12<15:
                Hand_state_name ="Stop"
            else:
                Hand_state_name = self.Chooseing_hand_state(Finger_data)

        elif Left_lm_coords:
            Hand_rotation = self.Get_hand_rotation(Left_lm_coords)
            Finger_data = self.Get_finger_states("Left", Hand_rotation, Left_lm_coords)

            degree_0_9 = self.Calculate_degree(Left_lm_coords[0][0], Left_lm_coords[0][1], Left_lm_coords[9][0], Left_lm_coords[9][1])
            degree_9_12 = self.Calculate_degree(Left_lm_coords[9][0], Left_lm_coords[9][1], Left_lm_coords[12][0], Left_lm_coords[12][1])
            degree_9_12 = abs(degree_9_12)
            
            if 75<degree_0_9<105 and 165<degree_9_12<180:
                Hand_state_name ="Stop"
            else:
                Hand_state_name = self.Chooseing_hand_state(Finger_data)

        return Hand_state_name

    def Set_Hand_states(self, Hands):
        Camera_RGB = cv2.cvtColor(self.Camera, cv2.COLOR_BGR2RGB)
        Camera_RGB.flags.writeable = False
        processed_camera = Hands.process(Camera_RGB)
        if processed_camera.multi_hand_landmarks:
            Left_lm_coords, Right_lm_coords = {}, {}
            for hand_landmarks, hand_info in zip(processed_camera.multi_hand_landmarks, processed_camera.multi_handedness): #This for loop works twice;one for right, one for left.
                self.mp_Draw.draw_landmarks(self.Camera, hand_landmarks, self.mp_Hands.HAND_CONNECTIONS) #Drawing Landmarks

                hand_type = hand_info.classification[0].label #"Right","Left"
                if hand_type == "Right":
                    for id , lm in enumerate(hand_landmarks.landmark):
                        h, w, c = self.Camera.shape
                        cx , cy = int(lm.x * w), int(lm.y * h)
                        Right_lm_coords[id] = (cx, cy)
                                
                if hand_type == "Left":
                    for id , lm in enumerate(hand_landmarks.landmark):
                        h, w, c = self.Camera.shape
                        cx , cy = int(lm.x * w), int(lm.y * h)
                        Left_lm_coords[id] = (cx, cy)

            self.Hand_state_name = self.Get_player_hand_state(Right_lm_coords, Left_lm_coords)
        else:
            self.Hand_state_name = "Waiting..."

    # OPENCV & CAMERA
    def Get_available_cameras(self, maximum_index=10):
        a_time = time.time()
        self.available_camera_list = []
        index = 0
        while index <= maximum_index:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                self.available_camera_list.append(index)
                cap.release()
            index += 1

    def Switch_camera(self, delta):
        if not self.available_camera_list:
            self.Camera = np.zeros((self.Camera_height, self.Camera_width, 3), dtype=np.uint8)
            camera_error_text = "No camera detected! Please plug in a camera and restart the game."
            camera_error_text_size = cv2.getTextSize(camera_error_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)[0]
            cv2.putText(self.Camera, camera_error_text,
                        ((self.Camera_width-camera_error_text_size[0])//2, (self.Camera_height+camera_error_text_size[1])//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 2, cv2.LINE_AA)
        
        self.cap.release()
        
        self.camera_list_index = (self.camera_list_index + delta) % len(self.available_camera_list)
        self.camera_index = self.available_camera_list[self.camera_list_index]
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.Camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.Camera_height)

    # IMAGES & SOUND EFFECTS
    def Read_images(self):
        Hand_img_size_T_CR = (344,344) #Tutorial, Choosing_rounds
        Hand_img_size_P_RE_GE = (300,300) #Playing, Round_end, Game_end
        Icon_img_size = (93,93)
        Small_moai_Icon_img_size = (70,70)
        #Since the bot images is already have correct size didn't add Bot_img_size = (640,480)
        self.Image_Dict = {
            #Backgrounds
            "BG_Tutorial_img": cv2.imread(resource_path("RPS_files/Images/Backgrounds/BG_Tutorial.png")),
            "BG_Round_Selection_img": cv2.imread(resource_path("RPS_files/Images/Backgrounds/BG_Round_Selection.png")),
            "BG_Playing_img": cv2.imread(resource_path("RPS_files/Images/Backgrounds/BG_Playing.png")),
            "BG_Round_end_img": cv2.imread(resource_path("RPS_files/Images/Backgrounds/BG_Round_end.png")),
            "BG_Game_end_img": cv2.imread(resource_path("RPS_files/Images/Backgrounds/BG_Game_end.png")),
            "BG_Game_end_blue_img": cv2.imread(resource_path("RPS_files/Images/Backgrounds/BG_Game_end_blue.png")),
            "BG_Game_end_red_img": cv2.imread(resource_path("RPS_files/Images/Backgrounds/BG_Game_end_red.png")),

            #Bot_faces
            "Bot_smile_img": cv2.imread(resource_path("RPS_files/Images/Bot_faces/bot_smile.png")),
            "Bot_won_img": cv2.imread(resource_path("RPS_files/Images/Bot_faces/bot_won.png")),
            "Bot_lost_img": cv2.imread(resource_path("RPS_files/Images/Bot_faces/bot_lost.png")),
            "Bot_draw_img": cv2.imread(resource_path("RPS_files/Images/Bot_faces/bot_draw.png")),

            #Hand_gestures //// Tutorial, Choosing_rounds
            "Rock_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/rock.png")), Hand_img_size_T_CR),
            "Paper_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/paper.png")), Hand_img_size_T_CR),
            "Scissor_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/scissor.png")), Hand_img_size_T_CR),
            "Waiting..._img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/waiting.png")), Hand_img_size_T_CR),
            "OK_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/thumbs_up.png")), Hand_img_size_T_CR),
            "Stop_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/stop.png")), Hand_img_size_T_CR),

            "One_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/1.png")), Hand_img_size_T_CR),
            "Two_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/2.png")), Hand_img_size_T_CR),
            "Three_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/3.png")), Hand_img_size_T_CR),
            "Four_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/4.png")), Hand_img_size_T_CR),

            #Hand_gestures_small //// Playing, Round_end, Game_end
            "Rock_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/rock.png")), Hand_img_size_P_RE_GE),
            "Paper_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/paper.png")), Hand_img_size_P_RE_GE),
            "Scissor_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/scissor.png")), Hand_img_size_P_RE_GE),
            "Waiting..._img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/waiting.png")), Hand_img_size_P_RE_GE),
            "OK_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/thumbs_up.png")), Hand_img_size_P_RE_GE),
            "Stop_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/stop.png")), Hand_img_size_P_RE_GE),

            "One_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/1.png")), Hand_img_size_P_RE_GE),
            "Two_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/2.png")), Hand_img_size_P_RE_GE),
            "Three_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/3.png")), Hand_img_size_P_RE_GE),
            "Four_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Hand_gestures/4.png")), Hand_img_size_P_RE_GE),

            #Icons
            "icon_Moai_img_small": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Icons/icon_Moai.png")), Small_moai_Icon_img_size),
            "icon_Moai_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Icons/icon_Moai.png")), Icon_img_size),
            "icon_Crown_img": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Icons/icon_Crown.png")), Icon_img_size),
            "icon_Shield_blue": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Icons/icon_Shield_blue.png")), Icon_img_size),
            "icon_Shield_red": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Icons/icon_Shield_red.png")), Icon_img_size),
            "icon_Sword_blue": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Icons/icon_Sword_blue.png")), Icon_img_size),
            "icon_Sword_red": cv2.resize(cv2.imread(resource_path("RPS_files/Images/Icons/icon_Sword_red.png")), Icon_img_size)}

        missing_images = [name for name, value in self.Image_Dict.items() if value is None]
        if missing_images: print(f"ERROR: Could not find these images: {', '.join(missing_images)}") ; self.Quit_game = True

    def Load_sounds(self):
        pygame.mixer.init()
        try:
            self.Time_sfx_1 = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Time_sfx_1.wav"))
            self.Time_sfx_2 = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Time_sfx_2.wav"))
            self.Transition_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Transition_sfx.wav"))
            self.Selection_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Selection_sfx.wav"))
            self.Trumpet_lost_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Trumpet_lost_sfx.wav"))
            self.Trumpet_won_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Trumpet_won_sfx.wav"))
            self.Trumpet_draw_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Trumpet_draw_sfx.wav"))
            self.Rock_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Rock_sfx.wav"))
            self.Paper_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Paper_sfx.wav"))
            self.Scissor_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Scissor_sfx.wav"))
            self.Draw_sword_sfx = pygame.mixer.Sound(resource_path("RPS_files/Sound_effects/Draw_sword_sfx.wav"))
            pygame.mixer.music.load(resource_path("RPS_files/Sound_effects/Background_music.mp3"))

            self.Rock_sfx.set_volume(0.7)
            self.Paper_sfx.set_volume(0.75)
            self.Scissor_sfx.set_volume(0.9)
            self.Draw_sword_sfx.set_volume(0.85)
            self.Trumpet_lost_sfx.set_volume(0.8)
            self.Trumpet_won_sfx.set_volume(0.8)
            self.Trumpet_draw_sfx.set_volume(0.8)
            
        except Exception as error:
            print(f"An error has been occured while loading sound effects: {error}")
            self.Quit_game = True
        
        self.Time_sfx_loop_counter = 1
        self.ROUND_END_sfx_played = False
        self.GAME_END_sfx_played = False
        self.Dominant_sfxs = [self.Trumpet_lost_sfx, self.Trumpet_won_sfx, self.Trumpet_draw_sfx, self.Rock_sfx, self.Paper_sfx , self.Scissor_sfx, self.Draw_sword_sfx]

    def Music_volume_adjuster(self):
        if pygame.mixer.get_busy():
            for item in self.Dominant_sfxs:
                if item.get_num_channels() > 0:
                    pygame.mixer.music.set_volume(0.12)
        else: pygame.mixer.music.set_volume(0.18)

    def Time_sound_player(self):
        if self.Time_sfx_loop_counter %2 == 1: self.Time_sfx_1.play()
        elif self.Time_sfx_loop_counter %2 == 0: self.Time_sfx_2.play()
        self.Time_sfx_loop_counter += 1

    # TRANSITION
    def Start_Transition(self, next_game_state):
        self.Transition_start_time = time.time()
        self.Transition_next_game_state = next_game_state
        self.Transition_phase = 1
        self.Time_stop = True
    
    def Do_Transition_Circule(self):
        if self.Transition_phase > 0:
            Current_time = time.time()
            Time_diff =  Current_time - self.Transition_start_time
            if Time_diff > 0.09:
                self.Transition_loop_counter += 1
                self.Transition_start_time = Current_time

            if self.Transition_phase == 1:
                cv2.circle(self.master_canvas, (960,540), self.Transition_loop_counter*self.Circule_Arrow_Length + (self.Circule_Border_thickness/2).__ceil__() + self.Circule_A_C_gap + self.Circule_A_B_gap, (0,255,0), self.Circule_Border_thickness, cv2.LINE_AA)
                cv2.circle(self.master_canvas, (960,540), self.Transition_loop_counter*self.Circule_Arrow_Length + self.Circule_A_C_gap + self.Circule_A_B_gap, (0,0,0), -1, cv2.LINE_AA)

                cv2.arrowedLine(self.master_canvas, (960 - self.Circule_A_C_gap - (self.Transition_loop_counter-1)*self.Circule_Arrow_Length, 540),
                                                    (960 - self.Circule_A_C_gap - self.Transition_loop_counter*self.Circule_Arrow_Length, 540),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #left arrow
                
                cv2.arrowedLine(self.master_canvas, (960 + self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length, 540),
                                                    (960 + self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length, 540),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #right arrow
                
                cv2.arrowedLine(self.master_canvas, (960, 540 - self.Circule_A_C_gap - (self.Transition_loop_counter-1)*self.Circule_Arrow_Length),
                                                    (960, 540 - self.Circule_A_C_gap - self.Transition_loop_counter*self.Circule_Arrow_Length),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #top arrow
                
                cv2.arrowedLine(self.master_canvas, (960, 540 + self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length),
                                                    (960, 540 + self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #bottom arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 - (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #left top arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 + (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #right top arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 + (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #right bottom arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 - (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + (self.Transition_loop_counter-1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #left bottom arrow

                if self.Transition_loop_counter == 5 and not self.Transition_sfx_played:
                    self.Transition_sfx.play()
                    self.Transition_sfx_played = True

                if self.Transition_loop_counter == 6:
                    self.Transition_loop_counter = 0
                    self.Transition_phase = 2
                    self.Game_state = self.Transition_next_game_state
            
            elif self.Transition_phase == 2:
                cv2.circle(self.master_canvas, (960,540), 960, (0,0,0), (960- self.Transition_loop_counter*self.Circule_Arrow_Length)*2, cv2.LINE_AA)
                cv2.circle(self.master_canvas, (960,540), self.Transition_loop_counter*self.Circule_Arrow_Length + (self.Circule_Border_thickness/2).__ceil__(), (0,255,0), self.Circule_Border_thickness, cv2.LINE_AA)

                cv2.arrowedLine(self.master_canvas, (960 - self.Circule_A_C_gap*2 - self.Transition_loop_counter*self.Circule_Arrow_Length, 540), 
                                                    (960 - self.Circule_A_C_gap*2 - (self.Transition_loop_counter+1)*self.Circule_Arrow_Length, 540), 
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #left arrow
                
                cv2.arrowedLine(self.master_canvas, (960 + self.Circule_A_C_gap*2 + self.Transition_loop_counter*self.Circule_Arrow_Length, 540), 
                                                    (960 + self.Circule_A_C_gap*2 + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length, 540), 
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #right arrow
                
                cv2.arrowedLine(self.master_canvas, (960, 540 - self.Circule_A_C_gap*2 - self.Transition_loop_counter*self.Circule_Arrow_Length), 
                                                    (960, 540 - self.Circule_A_C_gap*2 - (self.Transition_loop_counter+1)*self.Circule_Arrow_Length), 
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #top arrow
                
                cv2.arrowedLine(self.master_canvas, (960, 540 + self.Circule_A_C_gap*2 + self.Transition_loop_counter*self.Circule_Arrow_Length), 
                                                    (960, 540 + self.Circule_A_C_gap*2 + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length), 
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #bottom arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 - (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #left top arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 + (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 - (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #right top arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 + (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #right bottom arrow
                
                cv2.arrowedLine(self.master_canvas, (round(960 - (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + self.Transition_loop_counter*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (round(960 - (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2), round(540 + (self.Circule_A_C_gap + (self.Transition_loop_counter+1)*self.Circule_Arrow_Length)*math.sqrt(2)/2)),
                                                    (0,255,0), 15, cv2.LINE_AA, tipLength=0.3) #left bottom arrow

                if self.Transition_loop_counter == 6:
                    self.Transition_loop_counter = 1
                    self.Transition_phase = 0
                    self.Time_stop = False
                    self.Transition_sfx_played = False

    def Display_FPS(self):
        current_time = time.time()
        time_difference = current_time - self.FPS_previous_time
        if time_difference > 0: fps = 1 / time_difference
        else: fps = 9999
        self.FPS_previous_time = current_time

        h, w, c = self.Camera.shape
        text_size = cv2.getTextSize(f"FPS: {round(fps)}", cv2.FONT_HERSHEY_DUPLEX, 0.75, 2)[0]
        cv2.rectangle(self.Camera, (w-110, 0), (w, 30), (0,0,0), -1) 
        cv2.putText(self.Camera, f"FPS: {round(fps)}", (w-55-round(text_size[0]/2), 15+round(text_size[1]/2)), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255,255,255), 2)

    # STARTER & MAIN
    def Set_starting_settings(self):
        #---------- Camera ----------
        self.Get_available_cameras()
        if self.available_camera_list:
            self.cap = cv2.VideoCapture(self.available_camera_list[self.camera_list_index])
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.Camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.Camera_height)
        else:
            self.Camera = np.zeros((self.Camera_height, self.Camera_width, 3), dtype=np.uint8)
            camera_error_text = "No camera detected! Please plug in a camera and restart the game."
            camera_error_text_size = cv2.getTextSize(camera_error_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)[0]
            cv2.putText(self.Camera, camera_error_text,
                        ((self.Camera_width-camera_error_text_size[0])//2, (self.Camera_height+camera_error_text_size[1])//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 2, cv2.LINE_AA)

        #---------- Window ----------
        cv2.namedWindow("Rock Paper Scissor", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Rock Paper Scissor", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        self.master_canvas = np.full((1080, 1920, 3), 50, dtype=np.uint8)
        
        #---------- Mediapipe ----------
        self.mp_Hands = mp_hands
        self.mp_Draw = mp_drawing

    def Set_default_veriables(self):
        if self.Game_state == "TUTORIAL":
            self.Time_countdown_TUTORIAL = 5

        elif self.Game_state == "CHOOSING_ROUNDS":
            self.Time_countdown_CHOOSING_ROUNDS = 5
            self.Current_round = 1
            self.Player_score = 0
            self.Bot_score = 0
            self.Last_selectoin_index = None
            self.Time_sfx_loop_counter = 1

        if self.Game_state == "PLAYING":
            self.Time_countdown_PLAYING = 5
            self.Bot_state = "Smile"
            self.Bot_Hand_state_name = "Waiting..."
            self.Score_given = False

        if self.Game_state == "ROUND_END":
            self.Time_countdown_ROUND_END = 5
            self.Winner_text = ""
            self.Round_end_phrase = ""
            self.Score_given = False
            self.ROUND_END_sfx_played = False

        if self.Game_state == "GAME_END":
            self.Time_countdown_GAME_END = 5
            self.GAME_END_sfx_played = False

    def GAME_STATE_FUNC(self, display_fps=True):
        if not self.Background_music_started:
            pygame.mixer.music.set_volume(0.25)
            pygame.mixer.music.play(-1)
            self.Background_music_started = True

        if self.Last_frames_game_state != self.Game_state:
            self.Set_default_veriables()
            self.Last_frames_game_state = self.Game_state

        if self.Game_state == "TUTORIAL" or self.Game_state == "CHOOSING_ROUNDS":
            self.Camera = cv2.resize(self.Camera, (720, 540))

        if display_fps:
            self.Display_FPS() 

        if self.Time_stop:
            self.Previous_time = time.time()

        if self.Game_state == "TUTORIAL": self.TUTORIAL()
        elif self.Game_state == "CHOOSING_ROUNDS": self.CHOOSING_ROUNDS()
        elif self.Game_state == "PLAYING": self.PLAYING()
        elif self.Game_state == "ROUND_END": self.ROUND_END()
        elif self.Game_state == "GAME_END": self.GAME_END()

    def Main(self):
        self.Set_starting_settings()
        self.Read_images()
        self.Load_sounds()

        with self.mp_Hands.Hands(max_num_hands=2, model_complexity=0, min_detection_confidence=0.7, min_tracking_confidence=0.7) as Hands:
            while True:
                success , self.Camera = self.cap.read()
                if not success:
                    self.Camera = np.zeros((self.Camera_height, self.Camera_width, 3), dtype=np.uint8)
                    camera_error_text = "Camera signal lost. Press 'Q' or 'E' to switch devices." 
                    camera_error_text_size = cv2.getTextSize(camera_error_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                    cv2.putText(self.Camera, camera_error_text,
                                ((self.Camera_width-camera_error_text_size[0])//2, (self.Camera_height+camera_error_text_size[1])//2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
                if success:
                    self.Camera = cv2.flip(self.Camera, 1) #Mirror
                    self.Set_Hand_states(Hands)
                else: self.Hand_state_name = "Waiting..."

                #---------- GUI ----------
                self.GAME_STATE_FUNC()
                self.Do_Transition_Circule()
                self.Music_volume_adjuster()
                
                #---------- Show & Close ----------
                cv2.imshow("Rock Paper Scissor", self.master_canvas)
                if self.Quit_game: break

                pressing_key = cv2.waitKey(1) & 0xFF
                if pressing_key != 255:
                    if pressing_key == 27: break #ESC

                    elif pressing_key == ord("e") and time.time()-self.switch_camera_previous_time >= self.switch_camera_cooldown:
                        self.Switch_camera(1)
                        self.switch_camera_previous_time = time.time()

                    elif pressing_key == ord("q") and time.time()-self.switch_camera_previous_time >= self.switch_camera_cooldown: 
                        self.Switch_camera(-1)
                        self.switch_camera_previous_time = time.time()
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    Game = RPS_OpenCV()
    Game.Main()
