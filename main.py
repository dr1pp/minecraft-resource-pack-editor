import json
from tkinter import *
from tkinter.ttk import Combobox
from tkinter import filedialog
import os
from os.path import join, isfile
from shutil import move, copyfile
from PIL import Image, ImageTk


DEFAULT_RESOURCE_PACK_DIR = f"{os.getenv('APPDATA')}\.minecraft\\resourcepacks"
FORMAT_VERSIONS = {
    "1.6.1 – 1.8.9": 1,
    "1.9 – 1.10.2": 2,
    "1.11 – 1.12.2": 3,
    "1.13 – 1.14.4": 4,
    "1.15 – 1.16.1": 5,
    "1.16.2 – 1.16.5": 6,
    "1.17.x": 7,
    "1.18.x": 8
}

GREEN = '#99e09a'
RED = '#e09999'

def validate_dir(dir: str):
    try:
        os.makedirs(dir)
    except FileExistsError:
        pass
    return dir



class ScrollFrame(Frame):
    def __init__(self, parent, *args, **kwargs):
        self.canvas = Canvas(parent, highlightthickness=0)
        super().__init__(self.canvas, *args, **kwargs)
        self.scrollbar = Scrollbar(parent, orient=VERTICAL, command=self.canvas.yview)
        self.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.canvas.create_window((0, 0), window=self, anchor=NW)

        self.bind('<MouseWheel>', self.scroll)


    def scroll(self, event):
        self.canvas.yview_scroll(-1 * int((event.delta / 120)), 'units')


    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()


# Image formatted to be used dynamically within a tkinter UI
class TkImage(Label):
    def __init__(self, parent, image_dir=None, *args, **kwargs):
        if image_dir is not None:
            self.image = Image.open(image_dir)
            self.photo_image = ImageTk.PhotoImage(self.image)
            super().__init__(parent, image=self.photo_image, *args, **kwargs)
        else:
            super().__init__(parent, *args, **kwargs)

    def update_image(self, new_image):
        self.image = Image.open(new_image)


    def resize(self, size):
        self.image = self.image.resize(size)
        self.refresh_image()


    def set_new_dir(self, dir):
        self.image = Image.open(dir)


    def refresh_image(self):
        self.photo_image = ImageTk.PhotoImage(self.image)
        self.configure(image=self.photo_image)


class Pack:
    def __init__(self, pack_dir):
        self.dir = pack_dir
        self.textures_dir = validate_dir(f"{self.dir}/assets/minecraft/textures")
        self.block_textures_dir = self.textures_dir + '/block'
        self.blockstates_dir = self.dir + '/assets/minecraft/blockstates'
        self.models_dir = self.dir + '/assets/minecraft/models/block'
        self.block_names = [file.split(".")[0] for file in os.listdir(self.blockstates_dir) if isfile(f"{self.blockstates_dir}/{file}")]


    def get_blockstate_dir(self, block_name):
        return f"{self.blockstates_dir}/{block_name}.json"


    def get_block_texture_dir(self, block_name, index=None):
        if index is None:
            return f"{self.textures_dir}/block/{block_name}.png"
        else:
            return f"{self.textures_dir}/block/{block_name}/{index}.png"


    def update_variant(self, block_name, index, variant_data):
        blockstate_dir = self.get_blockstate_dir(block_name)
        with open(blockstate_dir, "r+") as f:
            data = json.load(f)
            data["variants"][""][index] = variant_data
            save_json(f, data)



# TODO : Variant class holding information about variant and all sub-variants (rotated & mirrored)

class Block:
    def __init__(self, pack, block_name):
        self.pack = pack
        self.name = block_name
        self.blockstate_dir = self.pack.get_blockstate_dir(self.name)
        self.prepare_files()
        self.textures_dir = join(self.pack.textures_dir, self.name)
        self.variants = []


    def get_variants(self):
        self.variants = [Variant(self, variant["model"]) for variant in self.read_blockstates()["variants"][""]]
        return self.variants


    def read_blockstates(self):
        with open(self.blockstate_dir) as f:
            data = json.load(f)
            return data


    def prepare_blockstates(self):
        with open(self.blockstate_dir, "r+") as f:
            data = json.load(f)
            if isinstance(data["variants"][""], dict):
                data["variants"][""] = [data["variants"][""]]
                data["variants"][""][0]["model"] = f"block/{self.name}/0"
            else:
                for i, state in enumerate(data["variants"][""]):
                    if state["model"].endswith(f"/{self.name}"):
                        data["variants"][""][i]["model"] = state["model"].replace(self.name, "0")
                    elif state["model"].endswith(f"/{self.name}_mirrored"):
                        data["variants"][""][i]["model"] = state["model"].replace(f"{self.name}_mirrored", "0_m")
            save_json(f, data)


    def create_models_folder(self):
        subdirs = [name for name in os.listdir(self.pack.models_dir) if not isfile(join(self.pack.models_dir, name))]
        if self.name not in subdirs:
            new_dir = join(self.pack.models_dir, self.name)
            os.mkdir(new_dir)
            move(f"{self.pack.models_dir}/{self.name}.json", f"{new_dir}/0.json")


    def create_texture_folder(self):
        subdirs = [name for name in os.listdir(self.pack.block_textures_dir) if
                   not isfile(join(self.pack.block_textures_dir, name))]
        if self.name not in subdirs:
            new_dir = f"{self.pack.block_textures_dir}/{self.name}"
            os.mkdir(new_dir)
            move(self.pack.get_block_texture_dir(self.name), f"{new_dir}/0.png")


    def prepare_files(self):
        self.prepare_blockstates()
        self.create_models_folder()
        self.create_texture_folder()


    def add_variant(self, img_dir):
        self.add_texture(img_dir)
        self.handle_blockstates()
        self.add_model()
        self.get_variants()



class Variant:
    def __init__(self, block, model_path):
        self.block = block
        self.pack = self.block.pack
        self.model_path = model_path
        self.id = self.model_path.split("/")[-1]
        self.texture_dir = join(self.block.textures_dir, f"{self.id}.png")


    def build_frame(self, frame):
        return VariantListItem(frame, self.pack, )


    def delete(self):
        pass



class VariantListItem(Frame):
    def __init__(self, parent, pack, block_name, index):
        super().__init__(parent, bd=0, relief=RAISED)
        self.columnconfigure(0, minsize=70)
        self.pack = pack
        self.block_name = block_name
        self.index = index
        Label(self, text="Weight:").grid(row=0, column=2, padx=(30, 0), rowspan=2)
        self.weight_var = StringVar()
        self.weight_entry = Entry(self, textvariable=self.weight_var, width=5)
        self.weight_entry.grid(row=0, column=3, padx=(0, 30), rowspan=2)
        Label(self, text="X:").grid(row=0, column=4, padx=3)
        self.x_rotation_var = StringVar()
        self.x_rotation_entry = Entry(self, textvariable=self.x_rotation_var, width=5)
        self.x_rotation_entry.grid(row=0, column=5)
        Label(self, text="Y:").grid(row=1, column=4, padx=3)
        self.y_rotation_var = StringVar()
        self.y_rotation_entry = Entry(self, textvariable=self.y_rotation_var, width=5)
        self.y_rotation_entry.grid(row=1, column=5)
        Label(self, text="Y:").grid(row=1, column=4, padx=3)
        self.z_rotation_var = StringVar()
        self.z_rotation_entry = Entry(self, textvariable=self.z_rotation_var, width=5)
        self.z_rotation_entry.grid(row=1, column=5)


        # TODO : Add Z axis rotation and stack inputs vertically across rows

        with open(pack.get_blockstate_dir(self.block_name)) as f:
            data = json.load(f)
            variant_info = data["variants"][""][index]

        if "weight" in variant_info.keys():
            self.weight_var.set(variant_info["weight"])
        else:
            self.weight_var.set("0")
        if "x" in variant_info.keys():
            self.x_rotation_var.set(variant_info["x"])
        else:
            self.x_rotation_var.set("0")
        if "y" in variant_info.keys():
            self.y_rotation_var.set(variant_info["y"])
        else:
            self.y_rotation_var.set("0")

        self.model_id = variant_info["model"].split("/")[-1]
        self.texture_id = self.model_id.split("_")[0]

        Label(self, text=self.model_id).grid(row=0, column=0, padx=10, rowspan=2)
        self.texture = TkImage(self, pack.get_block_texture_dir(self.block_name, self.texture_id))
        self.texture.resize((70, 70))
        self.texture.grid(row=0, column=1, padx=(0, 10), rowspan=2)

        self.weight_var.trace("w", self.update_blockstate)
        self.x_rotation_var.trace("w", self.update_blockstate)
        self.y_rotation_var.trace("w", self.update_blockstate)


    def update_blockstate(self, name, mode, index):
        try:
            data = {"model": f"block/{self.block_name}/{self.model_id}",
                    "weight": int(self.weight_var.get()),
                    "y": int(self.y_rotation_var.get()),
                    "x": int(self.x_rotation_var.get())
                    }
        except:
            return
        self.pack.update_variant(self.block_name, self.index, data)


class UI(Tk):

    class NewPackWindow(Tk):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.title("Create new pack")
            self.iconbitmap("Anvil.ico")
            self.geometry("580x500")
            self.resizable(0, 0)
            self.draw()

        def draw(self):
            self.pack_dir_frame = Frame(self)
            self.pack_dir_frame.grid(row=0, sticky=NSEW)
            self.pack_dir_frame.columnconfigure(1, weight=1)

            Label(self.pack_dir_frame, text="Pack root directory:").grid(row=0, column=0, padx=(10, 5), pady=10)
            self.pack_dir_var = StringVar()
            self.pack_dir_var.trace("w", self.check_pack_directory)
            self.pack_dir_entry = Entry(self.pack_dir_frame, textvariable=self.pack_dir_var, width=60)
            self.pack_dir_entry.insert(END, DEFAULT_RESOURCE_PACK_DIR)
            self.pack_dir_entry.grid(row=0, column=1, padx=(5, 10), pady=10)
            Button(self.pack_dir_frame, text="Browse...", command=self.pack_dir_dialog).grid(row=0, column=2, padx=5, pady=10)


        def pack_dir_dialog(self):
            pack_dir = filedialog.askdirectory()
            self.pack_dir_entry.delete(0, END)
            self.pack_dir_entry.insert(0, pack_dir)


        def check_pack_directory(self, name, index, mode):
            try:
                if "pack.mcmeta" in os.listdir(self.pack_dir_var.get()):
                    self.pack_dir_entry.configure(bg=GREEN)
                    self.enable_children_of(self.block_frame)
                    self.pack = Pack(self.pack_dir_var.get())
                    self.block_name_entry["values"] = self.pack.block_names
                else:
                    self.pack_dir_entry.configure(bg=RED)
                    self.disable_children_of(self.block_frame)
                    self.block_name_entry["values"] = []
            except FileNotFoundError:
                self.pack_dir_entry.configure(bg=RED)
                self.disable_children_of(self.block_frame)
                self.block_name_entry["values"] = []


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pack = None
        self.title("Resource Pack Editor")
        self.iconbitmap("Anvil.ico")
        self.geometry("900x575")
        self.minsize(704, 575)
        self.create_menubar()
        self.draw()


    def draw(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.pack_dir_frame = Frame(self)
        self.pack_dir_frame.grid(row=0, sticky=NSEW)
        self.pack_dir_frame.columnconfigure(1, weight=1)

        Label(self.pack_dir_frame, text="Pack root directory:").grid(row=0, column=0, padx=(10, 5), pady=10)
        self.pack_dir_var = StringVar()
        self.pack_dir_var.trace("w", self.check_pack_directory)
        self.pack_dir_entry = Entry(self.pack_dir_frame, textvariable=self.pack_dir_var, width=800)
        self.pack_dir_entry.grid(row=0, column=1, padx=(5, 10), pady=10)
        Button(self.pack_dir_frame, text="Browse...", command=self.pack_dir_dialog).grid(row=0, column=2, padx=5, pady=10)

        self.block_frame = Frame(self, bd=2, relief=SUNKEN)
        self.block_frame.grid(row=1, column=0, sticky=NSEW)
        self.block_frame.columnconfigure(0, weight=1)
        self.block_frame.columnconfigure(1, weight=100000)
        self.block_frame.rowconfigure(1, weight=1)

        Label(self.block_frame, text="Block:").grid(row=0, column=0, padx=(10, 5), pady=10, sticky=W)
        self.block_name_var = StringVar()
        self.block_name_var.trace("w", self.block_combo_search)
        self.block_name_entry = Combobox(self.block_frame, textvariable = self.block_name_var, values=["None"])
        self.block_name_entry.bind("<<ComboboxSelected>>", self.draw_variant_list)
        self.block_name_entry.bind("<Return>", self.draw_variant_list)
        self.block_name_entry.grid(row=0, column=1, padx=(5, 10), pady=10, sticky=W)

        self.texture_list_frame = Frame(self.block_frame, bd=1, relief=SUNKEN)
        self.texture_list_frame.grid(row=1, sticky=NSEW, columnspan=5)
        self.texture_list = ScrollFrame(self.texture_list_frame)

        self.add_texture_frame = Frame(self.block_frame)
        self.add_texture_frame.grid(row=2, columnspan=2, sticky=EW+S)
        self.add_texture_frame.columnconfigure(2, weight=1)

        self.texture_adding_frame = Frame(self.add_texture_frame, width=156, height=156, bd=1, relief=SUNKEN)
        self.texture_adding_frame.grid(row=0, column=0, padx=10, pady=10, columnspan=2, rowspan=2, sticky=W)
        self.texture_adding_frame.grid_propagate(0)
        self.no_image_label = Label(self.texture_adding_frame, text="No image selected")
        self.no_image_label.grid(row=0, column=0, sticky=NSEW, padx=25, pady=65)
        self.texture = TkImage(self.texture_adding_frame)
        self.texture.grid(row=0, column=0, sticky=NSEW)
        self.texture.grid_remove()

        Label(self.add_texture_frame, text="Image directory:").grid(row=0, column=1, padx=(180, 5), pady=10)
        self.img_dir_var = StringVar()
        self.img_dir_var.trace("w", self.check_img_directory)
        self.img_dir_entry = Entry(self.add_texture_frame, textvariable=self.img_dir_var, width=800)
        self.img_dir_entry.grid(row=0, column=2, padx=(5, 10), pady=10)
        Button(self.add_texture_frame, text="Browse...", command=self.img_dir_dialog).grid(row=0, column=3, padx=10, pady=10)

        Button(self.add_texture_frame, text="Add texture", command=self.add_variant, height=2).grid(row=1, column=3,
                                                                                                    padx=10,
                                                                                                    pady=(20, 10))

        self.disable_children_of(self.block_frame)


    def block_combo_search(self, name, mode, index):
        self.block_name_entry["values"] = [result for result in self.pack.block_names if result.startswith(self.block_name_var.get())]


    def enable_children_of(self, widget):
        try:
            widget.configure(state="normal")
        except TclError:
            pass
        for child in widget.winfo_children():
            self.enable_children_of(child)


    def disable_children_of(self, widget):
        try:
            widget.configure(state="disabled")
        except TclError:
            pass
        for child in widget.winfo_children():
            self.disable_children_of(child)


    def pack_dir_dialog(self):
        pack_dir = filedialog.askdirectory()
        self.pack_dir_entry.delete(0, END)
        self.pack_dir_entry.insert(0, pack_dir)


    def img_dir_dialog(self):
        img_dir = filedialog.askopenfilename()
        self.img_dir_entry.delete(0, END)
        self.img_dir_entry.insert(0, img_dir)


    def add_variant(self):
        img_dir = self.img_dir_entry.get()
        block_name = self.block_name_entry.get()
        self.pack.add_variant(block_name, img_dir)
        self.draw_variant_list()


    def check_pack_directory(self, name, index, mode):
        try:
            if "pack.mcmeta" in os.listdir(self.pack_dir_var.get()):
                self.pack_dir_entry.configure(bg=GREEN)
                self.enable_children_of(self.block_frame)
                self.pack = Pack(self.pack_dir_var.get())
                self.block_name_entry["values"] = self.pack.block_names
            else:
                self.pack_dir_entry.configure(bg=RED)
                self.disable_children_of(self.block_frame)
                self.block_name_entry["values"] = []
        except FileNotFoundError:
            self.pack_dir_entry.configure(bg=RED)
            self.disable_children_of(self.block_frame)
            self.block_name_entry["values"] = []


    def check_img_directory(self, name, index, mode):
        img_dir = self.img_dir_var.get()
        try:
            if img_dir.endswith(".png"):
                self.no_image_label.grid_remove()
                self.img_dir_entry.configure(bg=GREEN)
                self.texture.set_new_dir(img_dir)
                self.texture.resize((150, 150))
                self.texture.grid()
            else:
                self.img_dir_entry.configure(bg=RED)
                self.no_image_label.grid()
        except FileNotFoundError:
            self.img_dir_entry.configure(bg=RED)
            self.no_image_label.grid()


    def draw_variant_list(self, e=None):
        self.block = Block(self.pack, self.block_name_var.get())
        variant_list_frames = []
        self.texture_list.clear()
        with open(self.block.blockstate_dir, "r+") as f:
            data = json.load(f)
            if "" in data["variants"].keys():
                if isinstance(data["variants"][""], dict):
                    data["variants"][""] = [data["variants"][""]]
            variants = data["variants"][""]
            for i, variant in enumerate(variants):
                try:
                    texture_id = int(variant["model"].split("/")[-1])
                except ValueError:
                    texture_id = 0
                variant_list_frames.append(VariantListItem(self.texture_list, self.pack, self.block.name, i))
                variant_list_frames[i].grid(row=i, pady=3, sticky=EW)
        self.texture_list.bind_all("<MouseWheel>", self.texture_list.scroll)


    def open_new_pack_window(self):
        new_pack_window = self.NewPackWindow()


    def create_menubar(self):
        menubar = Menu(self)

        file_menu = Menu(menubar, tearoff=False)
        file_menu.add_command(label="New pack", command=self.open_new_pack_window)
        menubar.add_cascade(label="File", menu=file_menu)

        self.config(menu=menubar)



def save_json(f, data):
    f.seek(0)
    json.dump(data, f, indent=4)
    f.truncate()


if __name__ == "__main__":
    ui = UI()
    ui.mainloop()
    ui.destroy()