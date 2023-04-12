import customtkinter
import tkinter
from time import sleep
import time
from datetime import datetime
import random
import RPi.GPIO as GPIO

from threading import Thread, enumerate as en
import threading

'''
A set of valid keys and non-alpha keys for determining keyboard presentation.
Valid keys are determined from what can be encoded into morse code.
'''
VALID_KEYS = [',','.','?','/','-','(',')','Q', 'W', 'E', 'R', 'T',
              'Y', 'U', 'I', 'O', 'P','A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
              'Z', 'X', 'C', 'V', 'B', 'N', 'M','1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
              'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p',
              'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l',
              'z', 'x', 'c', 'v', 'b', 'n', 'm', 'shift','space',"<---"]

NON_ALPANUM_KEYS = ['-', '=', '[', ']', ';', '\'', ',', '.', '/', " ", "_", "+", "{", "}", ":", "\"", "<", ">","?"]


'''
Take a message as a String, and return the encoded morse pattern in the form of ._ and spaces

When printing out to an LED, .=1 _=3 spaces = 1 in terms of time duration
we need 3 spaces between letters, and 7 spaces between words
i
'''
def encode_morse(message):

    encoded_message = ''

    morse_dict = {'A': '. -', 'B': '- . . .',
                  'C': '- . - .', 'D': '- . .', 'E': '.', 'F': '. . - .', 'G': '- - .', 'H': '. . . .', 'I': '. .',
                  'J': '. - - -', 'K': '- . -', 'L': '. - . .', 'M': '- -', 'N': '- .', 'O': '- - -', 'P': '. - - .',
                  'Q': '- - . -', 'R': '. - .', 'S': '. . .', 'T': '-', 'U': '. . -', 'V': '. . . -', 'W': '. - -',
                  'X': '- . . -', 'Y': '- . - -', 'Z': '- - . .',
                  '1': '. - - - -', '2': '. . - - -', '3': '. . . - -', '4': '. . . . -', '5': '. . . . .',
                  '6': '- . . . .',  '7': '- - . . .', '8': '- - - . .', '9': '- - - - .', '0': '- - - - -',
                  ',': '- - . . - -', '.': '. - . - . -', '?': '. . - - . .', '/': '- . . - .',
                  '-': '- . . . . -', '(': '- . - - .', ')': '- . - - . -'}



    for character in message:
        #convert to uppercase, no such thing as case in morse code
        character = character.upper()
        if character != ' ':
            encoded_message += morse_dict[character] + '   '
        else:
            encoded_message += '       '

    return(encoded_message)



'''
KeyboardButton class, extends CTkButton
instances of this class will make up the buttons used on the keyboard.  Because we are typing a message in morse code
we may want some buttons to be disabled to ensure the user cannot press them.  However, it's sometimes important to 
keep the overall layout of the keyboard intact, so provide a level of familiarisation to the input method.

Non alpha keys are displayed in a different colour for aesthetics
keys that are invalid morse keys are disabled and coloured differently

It is possible to call this constructor twice for two versions of the keys, either upper or lower case.
Then, you can use the parent class modifier .lower() or .lift() to change the layer height of the created object

This is much faster than redrawing them from scratch, expecially on a rasp pi.

'''
class KeyboardButton(customtkinter.CTkButton):
    def __init__(self, *args,
                 width: int = 64,
                 height: int = 64,
                 letter: 'a',
                 **kwargs):
        super().__init__(*args, width=width, height=height, **kwargs)

        self.letter = letter

        self.configure(text=letter, font=customtkinter.CTkFont(family="Courier New", weight='bold', size=40))

        if self.letter in NON_ALPANUM_KEYS:
            self.configure(fg_color="#323ca8")

        # Disable keys that don't translate into Morse
        if self.letter not in VALID_KEYS:
            self.configure(state=tkinter.DISABLED, fg_color="#3b3537")


'''
Shift button extends Keyboard button
Change appearance of the shift key based on current status of shift
'''
class ShiftButton(KeyboardButton):
    def __init__(self, *args,
                 shift: "False",
                 **kwargs):
        super().__init__(*args, **kwargs)

        if not shift:
            self.configure(fg_color="#323ca8", text="shift")
        else:
            self.configure(fg_color="#323ca8", text="SHIFT")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.encoded_message = None
        self.title("Morse Code")
        self.minsize(1024, 600)
        self.attributes('-fullscreen', True)

        # The only two things we really need to track are the current shift state, and the compiled string
        self.shift = False
        self.label = "_"

        # We are going to spawn a thread to display the morse, so that it doesn't lock up the app
        self.thread = None
        self.stop_thread = False

        # Master frame

        self.configure(fg_color="#94bdf2")

        # TOP FRAMES

        self.frame_text = customtkinter.CTkFrame(self, width=800, fg_color="#94bdf2")
        self.frame_text.grid_propagate(0)
        self.frame_submit = customtkinter.CTkFrame(self, width=1024 - 800, fg_color="#94bdf2")
        self.frame_submit.grid_propagate(0)

        self.frame_text.grid(row=0, column=0)
        self.frame_submit.grid(row=0, column=1)

        # Text box is actually a label.  This looks better when the user only has a touch screen interface
        self.text_box = customtkinter.CTkLabel(self.frame_text, text=self.label, text_color="black",
                                               font=customtkinter.CTkFont(
                                                   family="Courier New", weight='bold', size=80
                                               ))
        self.text_box.grid(row=0, column=0, sticky='nsew', padx=20)
        self.frame_text.rowconfigure(0, weight=1)

        self.submit_button = customtkinter.CTkButton(self.frame_submit, text="submit", height=90,
                                                     font=customtkinter.CTkFont(
                                                         family="Courier New", weight='bold', size=40
                                                     ), command=self.submitPress)
        self.quit_button = customtkinter.CTkButton(self.frame_submit, text="x", width=64, height=64,
                                                   font=customtkinter.CTkFont(
                                                       family="Courier New", weight='bold', size=20
                                                   ), command=self.on_closing)
        self.led_button = customtkinter.CTkButton(self.frame_submit, text="led", width=64, height=64,
                                                  font=customtkinter.CTkFont(
                                                      family="Courier New", weight='bold', size=20
                                                  ), state=tkinter.DISABLED, fg_color="#121111", corner_radius=32)
        self.quit_button.grid(row=0, column=0, padx=20, sticky='ne')
        self.led_button.grid(row=0, column=0, padx=20, sticky='nw')
        self.submit_button.grid(row=1, column=0, sticky='news', padx=20)
        self.frame_submit.rowconfigure((0), weight=1)
        self.frame_submit.rowconfigure((1), weight=1)
        self.frame_submit.columnconfigure(0, weight=1)



        # KEYBOARD FRAMES
        # 5 frames for 5 rows of the keyboard
        self.frame_buttons_1 = customtkinter.CTkFrame(self, fg_color="#94bdf2")
        self.frame_buttons_2 = customtkinter.CTkFrame(self, fg_color="#94bdf2")
        self.frame_buttons_3 = customtkinter.CTkFrame(self, fg_color="#94bdf2")
        self.frame_buttons_4 = customtkinter.CTkFrame(self, fg_color="#94bdf2")
        self.frame_buttons_5 = customtkinter.CTkFrame(self, fg_color="#94bdf2")


        # Build the uppercase characters first
        self.shift = True
        self.list_of_uppers = self.createKeyboard()

        # Then lay the lower case characters on top, so that they are the first ones seen by the user
        # We have two keyboards, and hitting shift will toggle them up or down accordingly
        self.shift = False
        self.list_of_lowers = self.createKeyboard()


        self.frame_buttons_1.grid(row=1, column=0, columnspan=2, sticky='ns')
        self.frame_buttons_2.grid(row=2, column=0, columnspan=2, sticky='ns')
        self.frame_buttons_3.grid(row=3, column=0, columnspan=2, sticky='ns')
        self.frame_buttons_4.grid(row=4, column=0, columnspan=2, sticky='ns')
        self.frame_buttons_5.grid(row=5, column=0, columnspan=2, sticky='ns')

        self.rowconfigure((0), weight=1)
        self.columnconfigure((0), weight=1)
        self.columnconfigure(1, weight=1)

    '''
    CreateKeyboard iterates through the list of letters and creates all the buttons required
    Changes to either upper or lower case depending on self.shift status (true or false)
    
    returns a list of keys, so that we can address them all later    
    '''

    def createKeyboard(self):

        list_of_buttons = []

        if self.shift:
            first_row = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+']
            second_row = ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{', '}']
            third_row = ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':', '\"']
            fourth_row = ['Z', 'X', 'C', 'V', 'B', 'N', 'M', '<', '>', '?']


        else:
            first_row = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=']
            second_row = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']']
            third_row = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'']
            fourth_row = ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/']

        for i, each in enumerate(first_row):
            list_of_buttons.append(
                KeyboardButton(self.frame_buttons_1, letter=each, command=lambda letter=each: self.buttonPress(letter)))
            list_of_buttons[-1].grid(row=0, column=i, padx=5, pady=5)

        # add the backspace key
        list_of_buttons.append(
            KeyboardButton(self.frame_buttons_1, letter="<---", width=120, command=self.backspacePress))
        list_of_buttons[-1].grid(row=0, column=i + 1, padx=5, pady=5)

        for i, each in enumerate(second_row):
            list_of_buttons.append(
                KeyboardButton(self.frame_buttons_2, letter=each, command=lambda letter=each: self.buttonPress(letter)))
            list_of_buttons[-1].grid(row=0, column=i, padx=5, pady=5)

        for i, each in enumerate(third_row):
            list_of_buttons.append(
                KeyboardButton(self.frame_buttons_3, letter=each, command=lambda letter=each: self.buttonPress(letter)))
            list_of_buttons[-1].grid(row=0, column=i, padx=5, pady=5)

        # add the shift key

        list_of_buttons.append(
            ShiftButton(self.frame_buttons_4, letter="shift", width=120, command=self.shiftPress,
                        shift=self.shift))
        list_of_buttons[-1].grid(row=0, column=0, padx=5, pady=5)

        for i, each in enumerate(fourth_row):
            list_of_buttons.append(
                KeyboardButton(self.frame_buttons_4, letter=each, command=lambda letter=each: self.buttonPress(letter)))
            list_of_buttons[-1].grid(row=0, column=i + 1, padx=5, pady=(5, 5))

        # add the shift key
        list_of_buttons.append(
            ShiftButton(self.frame_buttons_4, letter="shift", width=120, command=self.shiftPress,
                        shift=self.shift))
        list_of_buttons[-1].grid(row=0, column=i + 2, padx=5, pady=5)

        for i, each in enumerate(['space']):
            list_of_buttons.append(
                KeyboardButton(self.frame_buttons_5, letter=each, width=420,
                               command=lambda letter=each: self.buttonPress(letter)))
            list_of_buttons[-1].grid(row=0, column=i, padx=5, pady=(5, 10))

        return list_of_buttons

    '''
    submitPress callback
    
    called when submit is pressed, and creates a thread to execute the playMorse function
    HOWEVER, we don't want to spawn more than 1.  So we set the stop_thread toggle to True, and wait for the current
    child thread to end.  
    THis was causing issues on the pi (related to GPIO), where threads could become locked and non-responding
    To work around this, we only wait 1 second before we spawn a new thread.
    '''

    def submitPress(self):

        # submit the current string to the morse encoder

        self.encoded_message = encode_morse(self.label[:-1])
        self.stop_thread = True

        # wait until thread has ended, but some threads get stuck and it's tricky to end them, so give up after 1 sec
        time_now = time.time()
        while (threading.active_count() > 1 and time_now + 1 > time.time()):
            continue
        self.stop_thread = False
        self.thread = Thread(target=lambda message=self.encoded_message:self.playMorse(message), daemon=True)
        self.thread.start()

    '''
    This is our threaded function, which both sets the led button on the GUI and the GPIO connected to an LED
    
    We use a random selection of colour/leds so that we know if a new thread has been spawned.  This was mostly for 
    troubleshooting, but proved to be useful even during normal use
    '''

    def playMorse(self, message):

        colour = random.choice(["yellow","blue","red","orange",'pink','purple','green'])
        pin = random.choice([7,11,13])

        # Old threads may have left lights on, so let's quickly reset everything before we start displaying this msg
        GPIO.output(7, GPIO.LOW)
        GPIO.output(11, GPIO.LOW)
        GPIO.output(13, GPIO.LOW)
        self.led_button.configure(fg_color="#121111")

        for comp in message:
            if self.stop_thread:

                break
            elif comp == '.':

                self.led_button.configure(fg_color=colour)
                GPIO.output(pin, GPIO.HIGH)
                self.led_button.update()
                sleep(.3)

            elif comp == '-':
                self.led_button.configure(fg_color=colour)
                GPIO.output(pin, GPIO.HIGH)
                self.led_button.update()
                sleep(1)
            elif comp == ' ':
                self.led_button.configure(fg_color="#121111")
                GPIO.output(pin, GPIO.LOW)
                self.led_button.update()
                sleep(.3)

    '''
    shiftPress is called when the shift key is pressed.  We iterate through all current keys and lower/lift them
    to change the appearance and functionality of the keyboard
    '''
    def shiftPress(self):

        # Toggle the value of our shift, which will raise or lower the keyboard buttons as needed
        if self.shift:
            self.shift = False
            for each in self.list_of_uppers:
                each.lower()
            for each in self.list_of_lowers:
                each.lift()
        else:
            self.shift = True
            for each in self.list_of_uppers:
                each.lift()
            for each in self.list_of_lowers:
                each.lower()

    '''
    backspacePress removes the most recent character
    '''
    def backspacePress(self):

        if len(self.label) >= 2:
            # Fancy workaround to remove letter from second last position of a string
            self.label = self.label[:-2] + "_"

            self.text_box.configure(text=self.label)

    '''
    buttonPRess is attached to all normal keys on the keyboard.  On press, it adds the character to the current
    message string
    '''
    def buttonPress(self, letter):

        if letter == 'space':
            letter = " "

        if len(self.label) < 13:
            # Fancy workaround to append letter to the second last position of a string
            self.label = self.label[:-1] + letter + "_"

            self.text_box.configure(text=self.label)

    # Run in all instances of the program closing, to release the GUI elements and the GPIO pins
    def on_closing(self):
        GPIO.cleanup()
        self.destroy()

    # Used to help the application detect KeyboardInterrupts when GUI has focus
    def check(self):
        self.after(50, self.check)


if __name__ == "__main__":
    # # config the pins
    #
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(7, GPIO.OUT)
    GPIO.setup(11, GPIO.OUT)
    GPIO.setup(13, GPIO.OUT)
    #
    # set all low for the start
    for pin in (7, 11, 13):
        GPIO.output(pin, GPIO.LOW)

    app = App()
    app.after(50, app.check)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.bind("<Control-c>", app.on_closing)
    app.mainloop()
