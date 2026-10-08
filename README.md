# Typing Practice

Typing Practice is a desktop typing trainer based on python that helps to practice fast typing full texts while tracking the speed and accuracy across multiple modes. Practice modes to learn only the typing of letters, numbers, and punctuation are beside the main mode. Statistics about the delivered performance to track the training progress are also included. 

![alt text](./readme_utils/main_app.png)

![alt text](./readme_utils/statistics.png)

Happy typing! Track your streaks, experiment with sudden-death challenges, and iterate on the data that the trainer collects for you.


## Highlights
- **Flexible drills**: Switch between classic text runs, focused letter/number/symbol exercises - All modes are also executable in sudden-death settings or blind mode settings
- **Live feedback**: Timer, WPM, accuracy, and error count update with every keystroke so you know when to reset or push harder
- **Persistent history**: Each run will be saved, enabling comparisons of training vs. benchmark sessions
- **Charts built in**: Launch histograms and trend charts to visualize streaks, recent days, or per-mode performance
- **Ergonomics**: Follow the system theme or choose Light/Dark, resize fonts, and manage named texts


## Quick Start
1. Clone or download this repository
2. (Optional) Create and activate a virtual python environment
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Launch the trainer:
   ```powershell
   python main.py
   ```


## Using the App
1. Setup the app (dark mode, mode, training run/benchmark, text size)
2. Select if typing text mode or one of the helper modes shall be conducted
3. (Typing text)
   1. Pick either a text from the left-hand list or load a random one
   2. Click the input pane or press `Tab` to focus it, then start typing the displayed text
   3. Watch the status bar for elapsed time, WPM, total errors, and running error percentage
   4. When the text matches perfectly, the run is logged and the summary freezes so you can reflect or immediately start another round
4. (Helper mode)
   1. Select which mode to conduct
   2. Write the displayed character up to the 100th letter - the mode is then finished
5. Filter the stats by training/benchmark/combined and have a look on  histograms, rolling trends, or per-mode breakdowns


## Training Modes
- **Typing (default)**: Full text practice from your encrypted, ordered text library. Add your first text using **Manage texts**.
- **Letter / Special / Number drills**: Focused loops cycling through curated character sets
- **Sudden death**: Same drills but one mistake ends the session, logging how many perfect characters you managed
- **Blind mode**: Hides written text of the user and hides the live WPM/error readouts to learn to perfect the recognition when a key hit was wrong
- **Training run toggle**: Mark experiments separately; filters in the plotting UI treat the flag as its own dimension

Switch modes via the toolbar combobox and context buttons above the main panes.


## Data & Customization
- **Texts**: Open **Manage texts** to add named passages, edit or paste their content, delete with confirmation, and reorder by dragging or using Move up/down. Click **Save changes** to persist the library and update the main selection list. Closing with changes prompts to save or discard them. A run already loaded keeps its original text until you load another one.
- **Length goal**: The text manager suggests 400 characters and shows how many characters your text is below or above that goal. This is a suggestion, not a limit; spaces and actual newlines count as characters.
- **Whitespace**: The editor and preview wrap long lines automatically without inserting newline characters. Only line breaks already in the text (including those added with Enter) need to be typed during practice. The editor preserves the exact text, including trailing spaces, tabs and blank lines. Its live preview uses `·` for spaces, `⇥` for tabs, `↵` for newlines and explicit Unicode labels for other invisible characters. Preview symbols are never saved into your text. Typing practice uses the original saved content without adding line breaks or removing spaces.
- **Enter during practice**: At automatic wraps in the practice target, you can keep typing normally or press Enter. Between words, Enter may replace the separating space or accompany it. Optional Enter presses do not count as errors or extra characters/words. Actual newlines and blank lines saved in the text remain required. Accepted wrap points are captured when the exercise starts and stay fixed until reset or reload; if you resize or change the font during a run, reset to use its new wrap points.
- **Appearance**: **System** is the default and follows OS appearance changes while the app is open (within a few seconds). **Light** and **Dark** override it. System detection supports Windows, macOS, and Linux via the desktop settings portal with GNOME fallback; unavailable preferences default to light. Text size, theme preference and main window dimensions persist in `settings.json`. Window position, selected text, training options and unfinished runs are not restored.
- **Storage**: User data lives in the project’s Git-ignored `data/` folder, independent of the launch directory. `data/settings.json` stores appearance and window settings, `data/texts.json.enc` stores named texts, `data/*_stats.csv.enc` stores statistics, and `data/storage.key` unlocks the encrypted files. Keep the key together with your encrypted files when backing up or moving the project.
- **Encryption**: Texts and all regular, training, sudden-death and blind-mode statistics use authenticated [Fernet encryption](https://cryptography.io/en/latest/fernet/). Files use `.enc` extensions, and CSV statistics are decrypted only in memory for charts. Settings are plain JSON. Writes use atomic replacement. Modified encrypted files produce an error rather than silently resetting their contents.
- **Automatic unlocking**: No password is needed. A local `storage.key` unlocks the data; on Unix the key and data files are created with owner-only permissions. This deters casual editing rather than someone who can read the key and run their own code. Back up the entire data folder, including the key; losing the key makes encrypted data unreadable.
- **Git**: The entire `data/` folder, encrypted files, settings and local keys are ignored. User data stays local to the project and is not committed.

## Verification
Run the storage, theme and GUI regression tests without using your desktop:
```bash
xvfb-run -a -s '-screen 0 1920x1080x24' env -u WAYLAND_DISPLAY TYPING_PRACTICE_TEST_DISPLAY=isolated .venv/bin/python -m unittest discover -s tests -v
```
The tests use temporary user-data folders, mocked system appearance detection and an isolated display.
