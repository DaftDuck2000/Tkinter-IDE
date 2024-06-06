import sys
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog
import tkinter.ttk as ttk

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
        run_menu.add_command(label="Run Locally", command=self.run_local)

        menubar.add_cascade(label="Run", menu=run_menu)

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

        # Update line numbers when the content of the editor changes
        self.editor.bind('<KeyRelease>', self.update_line_numbers)
        self.editor.bind('<MouseWheel>', self.update_line_numbers)
        self.editor.bind('<Button-1>', self.update_line_numbers)

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

    def show_context_menu(self, event):
        # Select the item under the mouse pointer
        item = self.dir_tree.identify_row(event.y)
        if item:
            self.dir_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
        else:
            # If clicked on blank space, show a menu to create new file or folder
            self.context_menu_blank_space.post(event.x_root, event.y_root)

        # Create a context menu for blank space
        self.context_menu_blank_space = tk.Menu(self, tearoff=0)
        self.context_menu_blank_space.add_command(label="New File", command=self.new_file)
        # self.context_menu_blank_space.add_command(label="New Folder", command=self.new_folder)

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
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")

    def update_line_numbers(self, event=None):
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)

        for i in range(1, int(self.editor.index('end').split('.')[0])):
            self.line_numbers.insert(tk.END, f'{i}\n')

        self.line_numbers.config(state='disabled')

    def open_file(self):
        file_path = filedialog.askopenfilename(title='Open File')
        if file_path:
            self.open_file_path(file_path)

    def save_as(self):
        if self.current_file:
            file_path = filedialog.asksaveasfilename(initialfile=self.current_file, title='Save As')
        else:
            file_path = filedialog.asksaveasfilename(title='Save As')
        if file_path:
            try:
                with open(file_path, "w") as f:
                    f.write(self.editor.get('1.0', tk.END))
                self.current_file = file_path
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

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
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create new file: {e}")

    def run_local(self):
        if self.current_file:
            try:
                subprocess.run(["python", self.current_file])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to run file: {e}")

def main():
    app = MainWindow()
    app.mainloop()

if __name__ == '__main__':
    main()
