import sys
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog
import tkinter.ttk as ttk
import keyword as kw
import re

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title('Local Code')

        # Set the size and title of the window
        self.geometry('1600x900')

        # Set the icon for the window
        path = os.path.join("Icons", "Icon.png")
        if os.path.exists(path):
            self.iconphoto(True, tk.PhotoImage(file=path))

        # Create a menu bar
        menubar = tk.Menu(self)

        # Create File menu
        file_menu = tk.Menu(menubar, tearoff=0)

        # New File
        file_menu.add_command(label='New File', command=self.new_file)

        # Open Folder
        file_menu.add_command(label='Open Folder', command=self.open_folder)

        # Open File
        file_menu.add_command(label='Open File', command=self.open_file)

        # Save
        file_menu.add_command(label='Save', command=self.save)

        # Save As
        file_menu.add_command(label='Save As', command=self.save_as)

        menubar.add_cascade(label='File', menu=file_menu)

        # Run Menu
        run_menu = tk.Menu(menubar, tearoff=0)

        # Run Local
        run_menu.add_command(label="Run", command=self.run_local)

        menubar.add_cascade(label="Run", menu=run_menu)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)

        # Find
        edit_menu.add_command(label="Find", command=self.find_text)

        menubar.add_cascade(label="Edit", menu=edit_menu)

        self.config(menu=menubar)

        # Add a directory viewer
        self.dir_tree = ttk.Treeview(self)
        self.dir_tree.place(x=0, y=0, width=200, height=900)

        # Add a scrollbar to the directory viewer
        self.tree_scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.dir_tree.yview)
        self.tree_scrollbar.place(x=200, y=0, height=900)
        self.dir_tree.configure(yscrollcommand=self.tree_scrollbar.set)

        # Add a code editor with line numbers
        self.line_numbers = tk.Text(self, width=4, padx=3, takefocus=0, border=0,
                                    background='lightgrey', state='disabled', wrap='none')
        self.line_numbers.place(x=220, y=50, height=800)

        self.editor = scrolledtext.ScrolledText(self, wrap=tk.WORD)
        self.editor.place(x=260, y=50, width=1200, height=800)

        # Link scroll events
        self.editor.bind('<KeyRelease>', self.on_key_release)
        self.editor.bind('<MouseWheel>', self.sync_scroll)
        self.editor.bind('<Button-1>', self.update_line_numbers)
        self.editor.bind('<Button-4>', self.sync_scroll)  # For Linux
        self.editor.bind('<Button-5>', self.sync_scroll)  # For Linux

        self.line_numbers.bind('<MouseWheel>', self.sync_scroll)
        self.line_numbers.bind('<Button-4>', self.sync_scroll)  # For Linux
        self.line_numbers.bind('<Button-5>', self.sync_scroll)  # For Linux

        # Initialize current_file and current_folder
        self.current_file = ''
        self.current_folder = ''

        # Initially update line numbers
        self.update_line_numbers()

        # Bind the directory tree events
        self.dir_tree.bind('<<TreeviewOpen>>', self.open_node)
        self.dir_tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.dir_tree.bind('<Button-3>', self.show_context_menu)

        # Create a context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Rename", command=self.rename_item)
        self.context_menu.add_command(label="Delete", command=self.delete_item)

        # Create a context menu for blank space
        self.context_menu_blank_space = tk.Menu(self, tearoff=0)
        self.context_menu_blank_space.add_command(label="New File", command=self.new_file)
        # self.context_menu_blank_space.add_command(label="New Folder", command=self.new_folder)

        # Initialize search variables
        self.search_matches = []
        self.current_match_index = -1
        self.search_window = None

        # Add tags for syntax highlighting
        self.editor.tag_configure("keyword", foreground="blue")
        self.editor.tag_configure("string", foreground="green")
        self.editor.tag_configure("comment", foreground="grey")
        self.editor.tag_configure("function", foreground="purple")

    def show_context_menu(self, event):
        # Select the item under the mouse pointer
        item = self.dir_tree.identify_row(event.y)
        if item:
            self.dir_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
        else:
            # If clicked on blank space, show a menu to create new file or folder
            try:
                self.context_menu_blank_space.post(event.x_root, event.y_root)
            except:
                pass

    def rename_item(self):
        selected_item = self.dir_tree.selection()[0]
        old_path = self.dir_tree.item(selected_item, 'values')[0]

        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=os.path.basename(old_path))
        if new_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
                self.dir_tree.item(selected_item, text=new_name, values=[new_path])
                if old_path == self.current_file:
                    self.current_file = new_path
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename: {e}")

    def delete_item(self):
        selected_item = self.dir_tree.selection()[0]
        file_path = self.dir_tree.item(selected_item, 'values')[0]
        if messagebox.askyesno("Delete", f"Are you sure you want to delete '{os.path.basename(file_path)}'?"):
            try:
                if os.path.isdir(file_path):
                    os.rmdir(file_path)
                else:
                    os.remove(file_path)
                self.dir_tree.delete(selected_item)
                if file_path == self.current_file:
                    self.editor.delete('1.0', tk.END)
                    self.current_file = ''
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")

    def open_folder(self):
        folder_path = filedialog.askdirectory(title='Open Folder')
        if folder_path:
            self.current_folder = folder_path
            self.populate_tree(folder_path)

    def populate_tree(self, path):
        # Clear the existing tree
        self.dir_tree.delete(*self.dir_tree.get_children())
        self.insert_node('', path, path)

    def insert_node(self, parent, text, abspath):
        node = self.dir_tree.insert(parent, 'end', text=os.path.basename(abspath) or abspath, open=False, values=[abspath])
        if os.path.isdir(abspath):
            self.dir_tree.insert(node, 'end')

    def open_node(self, event):
        node = self.dir_tree.focus()
        abspath = self.dir_tree.item(node, 'values')[0]

        if os.path.isdir(abspath):
            # Clear children
            self.dir_tree.delete(*self.dir_tree.get_children(node))
            for p in os.listdir(abspath):
                self.insert_node(node, p, os.path.join(abspath, p))

    def on_tree_select(self, event):
        selected_item = self.dir_tree.selection()[0]
        file_path = self.dir_tree.item(selected_item, 'values')[0]
        if os.path.isfile(file_path) and (file_path.endswith('.txt') or file_path.endswith('.py')):
            self.save()
            self.open_file_path(file_path)

    def open_file_path(self, file_path):
        if file_path:
            try:
                with open(file_path, "r") as f:
                    self.editor.delete('1.0', tk.END)
                    self.editor.insert(tk.END, f.read())
                self.current_file = file_path
                self.update_line_numbers()
                self.highlight_syntax()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")

    def update_line_numbers(self, event=None):
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)

        for i in range(1, int(self.editor.index('end').split('.')[0])):
            self.line_numbers.insert(tk.END, f'{i}\n')

        self.line_numbers.config(state='disabled')

    def sync_scroll(self, event):
        # Get the current scroll position of the editor
        editor_scroll = self.editor.yview()
        # Update the scroll position of the line numbers to match the editor
        self.line_numbers.yview_moveto(editor_scroll[0])

    def open_file(self):
        file_path = filedialog.askopenfilename(title='Open File')
        if file_path:
            self.open_file_path(file_path)

    def save_as(self):
        if self.current_file:
            file_path = filedialog.asksaveasfilename(initialfile=self.current_file, title='Save As')
            if file_path:
                self.current_file = file_path
                self.save()

    def save(self):
        if self.current_file:
            try:
                with open(self.current_file, "w") as f:
                    f.write(self.editor.get('1.0', tk.END))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

    def new_file(self):
        file_path = filedialog.asksaveasfilename(title='New File')
        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write("# - Happy Coding! - #")
                self.editor.delete('1.0', tk.END)
                with open(file_path, "r") as f:
                    self.editor.insert(tk.END, f.read())
                self.current_file = file_path
                self.update_line_numbers()
                self.highlight_syntax()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create new file: {e}")

    def run_local(self):
        if self.current_file:
            try:
                subprocess.run(["python", self.current_file])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run file: {e}")

    def find_text(self):
        search_term = simpledialog.askstring("Find", "Enter text to find:")
        if search_term:
            self.highlight_text(search_term)
            self.create_search_window()

    def highlight_text(self, search_term):
        self.editor.tag_remove('highlight', '1.0', tk.END)
        self.search_matches = []
        start_pos = '1.0'
        while True:
            start_pos = self.editor.search(search_term, start_pos, stopindex=tk.END)
            if not start_pos:
                break
            end_pos = f'{start_pos}+{len(search_term)}c'
            self.editor.tag_add('highlight', start_pos, end_pos)
            self.search_matches.append((start_pos, end_pos))
            start_pos = end_pos
        self.editor.tag_config('highlight', background='yellow', foreground='black')
        self.current_match_index = 0
        self.scroll_to_match()

    def create_search_window(self):
        self.search_window = tk.Toplevel(self)
        self.search_window.title("Find")
        self.search_window.geometry("220x50")

        next_button = tk.Button(self.search_window, text="Next", command=self.next_match)
        next_button.pack(side=tk.LEFT, padx=10, pady=10)

        prev_button = tk.Button(self.search_window, text="Previous", command=self.previous_match)
        prev_button.pack(side=tk.LEFT, padx=10, pady=10)

        cancel_button = tk.Button(self.search_window, text="Cancel", command=self.cancel_search)
        cancel_button.pack(side=tk.LEFT, padx=10, pady=10)

    def scroll_to_match(self):
        if self.search_matches:
            match = self.search_matches[self.current_match_index]
            self.editor.see(match[0])
            self.editor.mark_set("insert", match[0])
            self.editor.tag_remove('current_match', '1.0', tk.END)
            self.editor.tag_add('current_match', match[0], match[1])
            self.editor.tag_config('current_match', background='orange')

    def next_match(self):
        if self.search_matches:
            self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
            self.scroll_to_match()

    def previous_match(self):
        if self.search_matches:
            self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
            self.scroll_to_match()

    def cancel_search(self):
        self.editor.tag_remove('highlight', '1.0', tk.END)
        self.editor.tag_remove('current_match', '1.0', tk.END)
        if self.search_window:
            self.search_window.destroy()
            self.search_window = None

    def on_key_release(self, event):
        self.highlight_syntax()
        self.update_line_numbers()

    def highlight_syntax(self):
        self.editor.tag_remove("keyword", "1.0", tk.END)
        self.editor.tag_remove("string", "1.0", tk.END)
        self.editor.tag_remove("comment", "1.0", tk.END)
        self.editor.tag_remove("function", "1.0", tk.END)

        content = self.editor.get("1.0", tk.END)

        # Keywords
        for kw_word in kw.kwlist:
            start_pos = "1.0"
            while True:
                start_pos = self.editor.search(r'\b' + kw_word + r'\b', start_pos, stopindex=tk.END, regexp=True)
                if not start_pos:
                    break
                end_pos = f"{start_pos}+{len(kw_word)}c"
                self.editor.tag_add("keyword", start_pos, end_pos)
                start_pos = end_pos

        # Strings
        for match in re.finditer(r'(\".*?\"|\'.*?\')', content):
            start_pos = f"1.0+{match.start()}c"
            end_pos = f"1.0+{match.end()}c"
            self.editor.tag_add("string", start_pos, end_pos)

        # Comments
        for match in re.finditer(r'#[^\n]*', content):
            start_pos = f"1.0+{match.start()}c"
            end_pos = f"1.0+{match.end()}c"
            self.editor.tag_add("comment", start_pos, end_pos)

        # Functions (highlighting the 'def' keyword and function name)
        for match in re.finditer(r'\bdef\b\s+(\w+)', content):
            start_pos = f"1.0+{match.start()}c"
            end_pos = f"1.0+{match.start()}c+3c"  # Highlight 'def'
            self.editor.tag_add("keyword", start_pos, end_pos)

            start_pos = f"1.0+{match.start(1)}c"
            end_pos = f"1.0+{match.end(1)}c"
            self.editor.tag_add("function", start_pos, end_pos)


def main():
    app = MainWindow()
    app.mainloop()

if __name__ == '__main__':
    main()
