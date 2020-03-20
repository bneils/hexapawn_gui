import pygame
import pygame_gui as pygui

from core import *
import os
import pickle
from math import sin, pi, ceil, exp
from time import time
from webbrowser import open as open_website
from random import randint, random
import ctypes

pygame.init()

# Author: Ben Neilsen
# Last edited: 3/20/20



class Pawn(pygame.sprite.Sprite):
    def __init__(self, image, pos, type, *groups):
        super().__init__(groups)

        self.image = image
        self.rect = image.get_rect()
        self.rect.topleft = pos
        self.type = type


class ShimmeringSprite:
    def __init__(self, display_surf, frames, index_func):
        """Frames should be a list of Surfaces, and index_func should receive values between 0 -> 360
        that give corresponding indices within the list of frames."""

        self.display_surf = display_surf
        self.frames = frames
        self.index_func = index_func
        self.rect = None
        self.size = frames[0].get_size()
        self.reset()

    def reset(self):
        """Resets the current animation"""
        self.start = None
        self.visible = False

    def draw(self):
        """Blit the current frame and move to the next."""
        if not self.visible:
            return

        if not self.start:
            self.start = time()

        self.display_surf.blit(self.frames[self.index_func(65 * (time() - self.start))], self.rect)


class ConfettiParticle(pygame.sprite.Sprite):
    def __init__(self, pos, size, master, *groups):
        super().__init__(*groups)
        self.color = (randint(0, 255), randint(0, 255), randint(0, 255))
        self.rect = pygame.Rect(pos, size)
        self.master = master
        self.alive = True
        
    def update(self):
        if self.rect.y > self.master.get_height():
            self.alive = False
            return
    
        pygame.draw.rect(self.master, self.color, self.rect)
        self.rect.y += randint(1, 2)
        self.rect.x += randint(-1, 1)


class Droplet(pygame.sprite.Sprite):
    def __init__(self, pos, master, *groups):
        super().__init__(*groups)
        self.rect = pygame.Rect(pos, (2, randint(5, 10)))
        self.master = master
        self.alive = True
       
    def update(self):
        if self.rect.y > self.master.get_height():
            self.alive = False
            return
        
        pygame.draw.rect(self.master, (14, 47, 194), self.rect)
        self.rect.y += randint(10, 15)
        self.rect.x += randint(-1, 1)


class GUI:
    def __init__(self):
        self.display_surf = pygame.display.set_mode((500, 500))
        pygame.display.set_caption("Hexapawn")
        pygame.display.set_icon(pygame.image.load('images/icon.png'))

        self.manager = pygui.UIManager(self.display_surf.get_size())
        self.manager.add_font_paths("fira_code", "D:\\AP Create Task\\themes\\FiraCode-Regular.ttf", "D:\\AP Create Task\\themes\\FiraCode-Bold.ttf")
        self.manager.add_font_paths("menlo", "D:\\AP Create Task\\themes\\Menlo.ttf")
        self.manager.preload_fonts([
            {"name": "fira_code", "point_size": 14, 'style': 'bold'},
            {"name": "fira_code", "point_size": 14, 'style': 'italic'},
            {"name": "fira_code", "point_size": 10, 'style': 'regular'}
        ])

        self.clock = pygame.time.Clock()
        self.fps = 60

        # Syntactic sugar
        self.width, self.height = self.display_surf.get_size()
        self.tile_width, self.tile_height = ceil(self.width / 3), ceil(self.height / 3)
        self.tile_size = (self.tile_width, self.tile_height)

        # Load important images
        self.tiles_image = pygame.transform.scale(pygame.image.load('images/tiles.png'), self.display_surf.get_size())
        self.blue_pawn = pygame.transform.scale(pygame.image.load('images/blue_pawn.png'), self.tile_size)
        self.red_pawn = pygame.transform.scale(pygame.image.load('images/red_pawn.png'), self.tile_size)


        # Prepare the images for pawn and tile highlighting masks
        self.yellow_pawn = pygame.transform.scale(pygame.image.load('images/yellow_pawn.png'), self.tile_size)
        self.yellow_square = pygame.surface.Surface(self.tile_size)
        self.yellow_square.fill((255, 255, 102))

        # Cache all surfaces for the varying opacities for the yellow square.
        self.transparent_yellow_squares = [self.im_set_alpha(self.yellow_square, alpha) for alpha in range(32, 96)]
        self.transparent_yellow_pawns   = [self.im_set_alpha(self.yellow_pawn,   alpha) for alpha in range(32, 96)]

        default_sessions = [p for p in self.get_bot_presets() if p.endswith("\\default_session.p")]
        self.current_preset = default_sessions[0] if default_sessions else ""
        self.can_click = True
        self.is_clicking = False
        
        self.title_btn = self.settings_btn = self.back_btn = self.gameover_btn = None

    def im_set_alpha(self, surface, alpha):
        """A better form of .set_alpha() that allows you to have per pixel opacity. Returns a new surface with that new opacity."""
        new_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        new_surf.blit(surface, (0, 0))

        alpha_img = pygame.Surface(surface.get_size(), pygame.SRCALPHA)   # Create image with certain opacity
        alpha_img.fill((255, 255, 255, alpha))

        new_surf.blit(alpha_img, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)  # "Blending" won't affect RGB (b/c any channel x1 is unchanged), but the
                                                                                # alpha channel will be.
        return new_surf

    def check_events(self):
        """Check the app's events and respond to them. Returns a function to call if an event is encountered."""

        # Maintain a flag to indicate whether or not the player has just
        # clicked their mouse (not holding)
        self.is_clicking = False
        if pygame.mouse.get_pressed()[0]:
            if self.can_click:
                self.can_click = False
                self.is_clicking = True
        else:
            self.can_click = True

        # Process all events
        for event in pygame.event.get():
            self.manager.process_events(event)

            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            elif event.type == pygame.USEREVENT:
                # Changing scenes
                if event.user_type == pygui.UI_BUTTON_PRESSED:
                    # Commence the game
                    if event.ui_element == self.title_btn:
                        self.title_btn.kill()
                        self.settings_btn.kill()

                        return self.play

                    # Enter settings
                    elif event.ui_element == self.settings_btn:
                        self.title_btn.kill()
                        self.settings_btn.kill()

                        return self.settings

                    # Return to the title (from settings)
                    elif event.ui_element == self.back_btn:
                        self.fps_slider.kill()
                        self.fps_label.kill()
                        self.back_btn.kill()
                        self.dropdown.kill()
                        self.warning_box.kill()
                        self.preset_label.kill()

                        return self.menu
                       
                    elif event.ui_element == self.gameover_btn:
                        self.gameover_btn.kill()
                        self.gameover_box.kill()
                        
                        return self.menu

                # A link was clicked in a UI text box. Open it with 'webbrowser'
                elif event.user_type == pygui.UI_TEXT_BOX_LINK_CLICKED:
                    open_website(event.link_target, new=2)

    def get_bot_presets(self):
        """Retrieve all file paths that end in .p"""
        presets = []
        for root_dir, dirs, files in os.walk("."):
            presets.extend([root_dir + "\\" + f for f in files if f.endswith(".p")])
        
        return presets


    def settings(self):
        """The GUI's settings interface."""

        # Create necessary elements
        self.fps_slider = pygui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect(self.width // 2 - self.width // 4, self.height // 10, self.width // 2, self.height // 15),
            start_value=self.fps, value_range=(15, 144), manager=self.manager
        )
        self.fps_label = pygui.elements.UILabel(
            text="%d FPS" % self.fps, relative_rect=pygame.Rect(self.width // 2 - self.width // 10, self.height // 30, self.width // 5, self.height // 15),
            manager=self.manager
        )
        self.back_btn = pygui.elements.UIButton(
            relative_rect=pygame.Rect(self.width // 2 - 100, int(self.height / 1.5), 200, 75),
            text="Back", manager=self.manager
        )
        self.warning_box = pygui.elements.UITextBox(
            html_text="<b>WARNING</b>: Pickling is <b>dangerous</b>. " + \
                      "Only unpickle files that you're familiar with. " + \
                      "See here: <i><a href='https://docs.python.org/3/library/pickle.html'>Read more</a></i>.",
            manager=self.manager, relative_rect=pygame.Rect((self.width // 2 - self.width // 4, self.height // 3 - self.height // 20 + 30), (self.width // 2, self.height // 5))
        )

        self.preset_label = pygui.elements.UILabel(text="Select a bot preset", manager=self.manager,
                                                    relative_rect=pygame.Rect(self.width // 2 - 250//2, self.height // 3 - self.height // 20 - 20, 250, 40))

        # Discover all files in the current directory and subdirectories that end in .p
        presets = [""] + self.get_bot_presets()

        # If what the user selected then doesn't exist now, purge it
        for path in presets:
            if path.endswith(self.current_preset):
                break
        else:
            self.current_preset = ""

        # Create the dropdown now that preset files are available
        self.dropdown = pygui.elements.UIDropDownMenu(options_list=presets, starting_option=self.current_preset,
                                                        relative_rect=pygame.Rect(self.width // 2 - self.width // 4, self.height // 2 + 30, self.width // 2, self.height // 15),
                                                        manager=self.manager)

        while True:
            func = self.check_events()
            if func:
                return func

            self.manager.update(self.clock.tick(self.fps) / 1000)

            # Allow the fps slider to have persistence
            self.fps_label.text = "%d FPS" % self.fps_slider.current_value
            self.fps_label.rebuild()
            self.fps = self.fps_slider.current_value

            # Record the current preset that was selected
            self.current_preset = self.dropdown.selected_option

            # Draw background and buttons
            self.display_surf.blit(self.tiles_image, (0, 0))
            self.manager.draw_ui(self.display_surf)

            pygame.display.flip()

    def menu(self):
        """The app's menu screen for navigation."""
        self.title_btn = pygui.elements.UIButton(relative_rect=pygame.Rect(self.width // 2 - 150, self.height // 2 - 100, 300, 100),
                                                            text="Play", manager=self.manager)
        self.settings_btn = pygui.elements.UIButton(relative_rect=pygame.Rect(self.width // 2 - 150, self.height // 2 + 50, 300, 100),
                                                            text="Settings", manager=self.manager)

        while True:
            func = self.check_events()  # Idiom to switch between screens
            if func:
                return func

            self.manager.update(self.clock.tick(self.fps) / 1000)

            # Draw background and buttons
            self.display_surf.blit(self.tiles_image, (0, 0))
            self.manager.draw_ui(self.display_surf)

            pygame.display.flip()

    def gameover(self):
        """Show the game over screen. Either rain or confetti will be created
        depending on who wins."""
        if self.winner == H:
            self.bot.inform_lost()
        
        self.gameover_box = pygui.elements.UITextBox(
            html_text="Congratulations, you won!" if self.winner == H else "Sorry, you've been outsmarted by the bot. Good luck next time.",
            manager=self.manager, relative_rect=pygame.Rect(self.width // 2 - self.width // 4, self.height // 2 - self.height // 4, self.width // 2, self.height // 2)
        )
        self.gameover_box.set_active_effect(pygui.TEXT_EFFECT_TYPING_APPEAR)
        
        # Make a white veil fall down across the screen w/ sigmoid curve
        white_veil = pygame.surface.Surface(self.display_surf.get_size())
        white_veil.fill((255, 255, 255))
        
        # Check https://www.desmos.com/calculator
        # and insert y=\left(\frac{1}{1+e^{-5x+7}}-1\right)\cdot500
        ani_start = time()
        elapsed = time() - ani_start
        frame_sec = 1 / self.fps
        while elapsed <= 1.9:
            self.check_events()
            
            y = int( 500 * (1 / (1 + exp(-7 * elapsed + 7)) - 1) )
            self.display_surf.blit(white_veil, (0, y))
            
            # If the player moves the window, everything freezes,
            # I need to increase the ani_start to mitigate this
            dt = self.clock.tick(self.fps) / 1000
            if dt > frame_sec:
                ani_start += dt - frame_sec 
            
            elapsed = time() - ani_start
            
            pygame.display.flip()
        
        # Make a button to allow the player to return to the title screen
        self.gameover_btn = pygui.elements.UIButton(
            text="Return to the title", manager=self.manager,
            relative_rect=pygame.Rect((self.width // 2 - self.width // 6, self.height * 5 // 6), 
                                      (self.width // 3, self.height // 10))
        )
        
        # Depending on the winner, rain or confetti will be spawned. These functions deal
        # with their respective particle
        if self.winner == H:
            make_more_particles = lambda: [ConfettiParticle( (randint(0, self.width), randint(0, 15)), (randint(1, 5), randint(1, 5)), self.display_surf ) for i in range(30)]
            threshhold_sec = lambda: random() / 2
        else:
            make_more_particles = lambda: [Droplet( (randint(0, self.width), randint(0, 15)), self.display_surf) for i in range(30)]
            threshhold_sec = lambda: random() / 10
            
        particles = pygame.sprite.Group(make_more_particles())
            
        # I will need to keep track of how often I add particles
        last_added = time()

        while True:
            self.manager.update(self.clock.tick(self.fps) / 1000)
            
            self.display_surf.fill((255, 255, 255))
            
            func = self.check_events()
            if func:
                # Save the pickle data if the player selected a preset.
                try:
                    with open(self.current_preset if self.current_preset else "default_session.p", 'wb') as f:
                        pickle.dump(self.bot, f)
                except pickle.PickleError as e:
                    pass
                finally:
                    if not self.current_preset:
                        self.current_preset = ".\\default_session.p"

                return func
            
            if time() - last_added > threshhold_sec():
                last_added = time()
                particles.add(make_more_particles())
            
            particles.update()
            particles.remove([p for p in particles.sprites() if not p.alive])

            self.manager.draw_ui(self.display_surf)
            pygame.display.flip()

    def play(self):
        """Play the game."""

        # Load the bot preset with pickle
        if self.current_preset:
            try:
                with open(self.current_preset, 'rb') as f:
                    self.bot = pickle.load(f)
            except (FileNotFoundError, pickle.PickleError, TypeError, EOFError) as e:
                # Make a UI popup to display that it failed.
                if e == FileNotFoundError:
                    error_message = "The file you're trying to load no longer exists"
                else:
                    error_message = "The file you're trying to load contains data in an <b>invalid format</b>. Only load files that were generated by this script!"

                popup = pygui.windows.ui_message_window.UIMessageWindow(
                                            message_window_rect=
                                                pygame.Rect(self.width // 2 - self.width // 4, self.height // 2 - self.height // 4,
                                                            self.width // 2, self.height // 2),
                                            message_title="Error loading bot preset.",
                                            html_message=error_message,
                                            manager=self.manager)
                self.current_preset = ""
                
                return self.menu
        else:
            self.bot = Bot()
        self.bot.play_again()

        # Initialize the board with pawns
        self.all_pawns = pygame.sprite.Group()
        board = [None] * 9
        for i in range(3):
            board[i] = Pawn(self.blue_pawn, (i * self.tile_width, 0), H, self.all_pawns)
            board[-i - 1] = Pawn(self.red_pawn, ((2 - i) * self.tile_width, 2 * self.tile_height), B, self.all_pawns)

        # For highlighting the currently selected pawn
        shimmering_pawn = ShimmeringSprite(self.display_surf, self.transparent_yellow_pawns, lambda d: int(255/16 * sin(d / 10) + 32))

        # For highlighting positions the selected pawn can move to
        shimmering_boxes = [ShimmeringSprite(self.display_surf, self.transparent_yellow_squares, lambda d: int(255/16 * sin(d / 10) + 32)) for i in range(3)]

        # Main loop
        while True:
            func = self.check_events()
            if func:
                return func

            self.clock.tick(self.fps) / 1000
            mouse_pos = pygame.mouse.get_pos()

            player_made_move = False
            # Update the list of selected pawns
            if self.is_clicking:
                # Detect whether or not the shimmering boxes have been clicked (The user's options)
                for i in range(3):
                    if shimmering_boxes[i].visible and shimmering_boxes[i].rect.collidepoint(mouse_pos):
                        # Positions inside the linear grid
                        last_pos = shimmering_pawn.rect.y // self.tile_height * 3 + \
                                        shimmering_pawn.rect.x // self.tile_width
                        new_pos = shimmering_boxes[i].rect.y // self.tile_height * 3 + \
                                        shimmering_boxes[i].rect.x // self.tile_width

                        # Animate the pawn moving
                        self._move_pawn(pawn, shimmering_boxes[i].rect.topleft)

                        # Move the pawn within the linear array (representing a matrix)
                        ## Remove pawn from the group
                        if board[new_pos]:
                            self.all_pawns.remove(board[new_pos])

                        ## Cut in list
                        board[new_pos] = board[last_pos]
                        board[last_pos] = None
                        player_made_move = True
                        break

                for pawn in self.all_pawns.sprites():
                    # Re-position the shimmering boxes
                    if pawn.type == H and pawn.rect.collidepoint(mouse_pos):
                        x, y = (pawn.rect.x // self.tile_width, pawn.rect.y // self.tile_height)
                        shimmering_pawn.rect = pawn.rect
                        shimmering_pawn.visible = True
                        selected_pawn = pawn

                        # Disable the boxes before re-evaluating whether
                        # they should be visible
                        for box in shimmering_boxes:
                            box.visible = False

                        # Find moves that the pawn can make and highlight those with a yellow box.
                        ## Check L and R diagonals (downwards)
                        ## The three boxes do not change X-values (only y).
                        if y <= 1:
                            shimmering_boxes[x].visible = board[(y + 1) * 3 + x] == None
                            if x >= 1:
                                diag_left = board[(y + 1) * 3 + (x - 1)]
                                shimmering_boxes[x - 1].visible = isinstance(diag_left, Pawn) and diag_left.type == B
                            if x <= 1:
                                diag_right = board[(y + 1) * 3 + (x + 1)]
                                shimmering_boxes[x + 1].visible = isinstance(diag_right, Pawn) and diag_right.type == B

                        # Re-position the boxes
                        for i in range(3):
                            shimmering_boxes[i].rect = pygame.Rect((i * self.tile_width, pawn.rect.y + self.tile_height), shimmering_boxes[i].size)
                        break

                # Nothing was selected
                else:
                    # Remove all shimmering objects
                    shimmering_pawn.reset()
                    for box in shimmering_boxes:
                        box.reset()
   

            # If the user made a move, then let the bot make one.
            if player_made_move:
                # Make win checks after each player's move.
                self.winner = win_check(board, H)
                if self.winner:
                    return self.gameover
                    
            
                dead_pawn, vector = self.bot.make_turn(board)
                
                if vector:
                    # The bot has moved the pawn to vector[1], so the transformation must
                    # reference the pawn in that location.
                    dest = vector[1] % 3 * self.tile_width, vector[1] // 3 * self.tile_height
                    self._move_pawn(board[vector[1]], dest)

                    # The shimmering boxes should disappear after the bot makes its move
                    shimmering_pawn.visible = False
                    for box in shimmering_boxes:
                        box.visible = False
                    
                    # Remove the dead pawn as a reference from the group
                    self.all_pawns.remove(dead_pawn)
                
                # Make a win check after the bot has completed its move
                self.winner = win_check(board, B)
                if self.winner:
                    return self.gameover
            

            self.display_surf.blit(self.tiles_image, (0, 0))
            self.all_pawns.draw(self.display_surf)

            # Draw a yellow filmy enchantment onto the selected pawn
            shimmering_pawn.draw()
            for box in shimmering_boxes:
                box.draw()

            pygame.display.flip()

        # Delete all references
        self.all_pawns.empty()


    def _move_pawn(self, pawn, dest):
        """Moves a sprite from one location to another."""

        dx, dy = (dest[0] - pawn.rect.x), (dest[1] - pawn.rect.y)

        # The actual pawn in question isn't moving, just it's image.
        # In order to do this we need to select all pawns but the one we want
        # and blit those
        other_pawns = pygame.sprite.Group([p for p in self.all_pawns.sprites() if p != pawn])

        ani_start = time()
        elapsed = 0
        frame_sec = 1 / self.fps

        # https://www.desmos.com/calculator
        # y=\frac{1}{1+e^{-\left(20x-6\right)}}

        while elapsed <= 0.7:
            # When moving the window, the ani pauses,
            # if it took too long to pause then add the diff onto the ani_start
            dt = self.clock.tick(self.fps) / 1000
            if dt > frame_sec:
                ani_start += dt - frame_sec
            elapsed = time() - ani_start
            
            self.check_events()
            
            self.display_surf.blit(self.tiles_image, (0, 0))
            other_pawns.draw(self.display_surf)
            
            sigmoid_val = 1 / (1 + exp(-(20 * elapsed - 6)))
            
            x = pawn.rect.x + sigmoid_val * dx
            y = pawn.rect.y + sigmoid_val * dy

            self.display_surf.blit(pawn.image, (int(x), int(y)))

            pygame.display.flip()

        # The group needs to be emptied in order to make sure that
        # when we want to delete sprites, all references are gone and
        # the garbage collector can do its job
        other_pawns.empty()
        pawn.rect.topleft = dest

    def run(self):
        """The GUI's interface."""
        func = self.menu
        while True:
            func = func()   # Func modifies itself in between screen switching


gui = GUI()
gui.run()
