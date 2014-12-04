# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Bswap Admin Tools",
    "author": "Pablo Vazquez, Matthew Muldoon",
    "version": (0, 1),
    "blender": (2, 71),
    "location": "Everywhere!",
    "description": "A collection of tools and settings to improve productivity",
    "warning": "",
    "wiki_url": "http://pablovazquez.org/amaranth",
    "tracker_url": "",
    "category": "Scene"}


import bpy
import bmesh
from bpy.types import Operator, AddonPreferences, Panel, Menu
from bpy.props import (BoolProperty, EnumProperty,
                       FloatProperty, FloatVectorProperty,
                       IntProperty, StringProperty)
from mathutils import Vector
from bpy.app.handlers import persistent
from bl_operators.presets import AddPresetBase

# Addon wide, we need to know if cycles is available
cycles_exists = False


def check_cycles_exists():
    global cycles_exists
    cycles_exists = ('cycles' in dir(bpy.types.Scene))    
return cycles_exists


check_cycles_exists()


# Preferences
class AmaranthToolsetPreferences(AddonPreferences):
    bl_idname = __name__
    use_scene_stats = BoolProperty(
    	name="Extra Scene Statistics",
        description="Display extra scene statistics in Info editor's header",
        default=True,
        )

# Scene Debug
    # Cycles Node Types
    if check_cycles_exists():
        cycles_shader_node_types = [
            ("BSDF_DIFFUSE", "Diffuse BSDF", "", 0),
            ("BSDF_GLOSSY", "Glossy BSDF", "", 1),
            ("BSDF_TRANSPARENT", "Transparent BSDF", "", 2),
            ("BSDF_REFRACTION", "Refraction BSDF", "", 3),
            ("BSDF_GLASS", "Glass BSDF", "", 4),
            ("BSDF_TRANSLUCENT", "Translucent BSDF", "", 5),
            ("BSDF_ANISOTROPIC", "Anisotropic BSDF", "", 6),
            ("BSDF_VELVET", "Velvet BSDF", "", 7),
            ("BSDF_TOON", "Toon BSDF", "", 8),
            ("SUBSURFACE_SCATTERING", "Subsurface Scattering", "", 9),
            ("EMISSION", "Emission", "", 10),
            ("BSDF_HAIR", "Hair BSDF", "", 11),
            ("BACKGROUND", "Background", "", 12),
            ("AMBIENT_OCCLUSION", "Ambient Occlusion", "", 13),
            ("HOLDOUT", "Holdout", "", 14),
            ("VOLUME_ABSORPTION", "Volume Absorption", "", 15),
            ("VOLUME_SCATTER", "Volume Scatter", "", 16)
            ]

        scene.amaranth_cycles_node_types = EnumProperty(
            items=cycles_shader_node_types, name = "Shader")

        scene.amaranth_cycles_list_sampling = BoolProperty(
            default=False,
            name="Samples Per:")

        bpy.types.CyclesRenderSettings.use_samples_final = BoolProperty(
            name="Use Final Render Samples",
            description="Use current shader samples as final render samples",
            default=False)

    scene.amaranth_lighterscorner_list_meshlights = BoolProperty(
        default=False,
        name="List Meshlights",
        description="Include light emitting meshes on the list")

    scene.amaranth_debug_scene_list_missing_images = BoolProperty(
        default=False,
        name="List Missing Images",
        description="Display a list of all the missing images")

    bpy.types.ShaderNodeNormal.normal_vector = prop_normal_vector
    bpy.types.CompositorNodeNormal.normal_vector = prop_normal_vector

    bpy.types.Object.is_keyframe = is_keyframe

    scene.amth_wire_toggle_scene_all = BoolProperty(
        default=False,
        name="All Scenes",
        description="Toggle wire on objects in all scenes")
    scene.amth_wire_toggle_is_selected = BoolProperty(
        default=False,
        name="Only Selected",
        description="Only toggle wire on selected objects")
    scene.amth_wire_toggle_edges_all = BoolProperty(
        default=True,
        name="All Edges",
        description="Draw all edges")
    scene.amth_wire_toggle_optimal = BoolProperty(
        default=False,
        name="Optimal Display",
        description="Skip drawing/rendering of interior subdivided edges "
                    "on meshes with Subdivision Surface modifier")

def clear_properties():
    props = (
        "use_unsimplify_render",
        "simplify_status",
        "use_matching_indices",
        "use_simplify_nodes_vector",
        "status",
        "types",
        "toggle_mute",
        "amaranth_cycles_node_types",
        "amaranth_lighterscorner_list_meshlights",
        "amaranth_debug_scene_list_missing_images",
        "amarath_cycles_list_sampling",
        "normal_vector",
        "use_samples_final",
        'amth_wire_toggle_is_selected',
        'amth_wire_toggle_scene_all',
        "amth_wire_toggle_edges_all",
        "amth_wire_toggle_optimal"
    )
    
    wm = bpy.context.window_manager
    for p in props:
        if p in wm:
            del wm[p]
# FEATURE: Scene Debug
class AMTH_SCENE_OT_cycles_shader_list_nodes(Operator):
    """List Cycles materials containing a specific shader"""
    bl_idname = "scene.cycles_list_nodes"
    bl_label = "List Materials"
    materials = []

    @classmethod
    def poll(cls, context):
        return cycles_exists and context.scene.render.engine == 'CYCLES'

    def execute(self, context):
        node_type = context.scene.amaranth_cycles_node_types
        roughness = False
        self.__class__.materials = []
        shaders_roughness = ['BSDF_GLOSSY','BSDF_DIFFUSE','BSDF_GLASS']

        print("\n=== Cycles Shader Type: %s === \n" % node_type)

        for ma in bpy.data.materials:
            if ma.node_tree:
                nodes = ma.node_tree.nodes
                
                print_unconnected = ('Note: \nOutput from "%s" node' % node_type,
                                        'in material "%s"' % ma.name, 'not connected\n')

                for no in nodes:
                    if no.type == node_type:
                        for ou in no.outputs:
                            if ou.links:
                                connected = True
                                if no.type in shaders_roughness:
                                    roughness = 'R: %.4f' % no.inputs['Roughness'].default_value
                                else:
                                    roughness = False
                            else:
                                connected = False
                                print(print_unconnected)

                            if ma.name not in self.__class__.materials:
                                self.__class__.materials.append('%s%s [%s] %s%s%s' % (
                                    '[L] ' if ma.library else '',
                                    ma.name, ma.users,
                                    '[F]' if ma.use_fake_user else '',
                                    ' - [%s]' % roughness if roughness else '',
                                    ' * Output not connected' if not connected else ''))

                    elif no.type == 'GROUP':
                        if no.node_tree:
                            for nog in no.node_tree.nodes:
                                if nog.type == node_type:
                                    for ou in nog.outputs:
                                        if ou.links:
                                            connected = True
                                            if nog.type in shaders_roughness:
                                                roughness = 'R: %.4f' % nog.inputs['Roughness'].default_value
                                            else:
                                                roughness = False
                                        else:
                                            connected = False
                                            print(print_unconnected)

                                        if ma.name not in self.__class__.materials:
                                            self.__class__.materials.append('%s%s%s [%s] %s%s%s' % (
                                                '[L] ' if ma.library else '',
                                                'Node Group:  %s%s  ->  ' % (
                                                    '[L] ' if no.node_tree.library else '',
                                                    no.node_tree.name),
                                                ma.name, ma.users,
                                                '[F]' if ma.use_fake_user else '',
                                                ' - [%s]' % roughness if roughness else '',
                                                ' * Output not connected' if not connected else ''))

                    self.__class__.materials = sorted(list(set(self.__class__.materials)))

        if len(self.__class__.materials) == 0:
            self.report({"INFO"}, "No materials with nodes type %s found" % node_type)
        else:
            print("* A total of %d %s using %s was found \n" % (
                    len(self.__class__.materials),
                    "material" if len(self.__class__.materials) == 1 else "materials",
                    node_type))

            count = 0

            for mat in self.__class__.materials:
                print('%02d. %s' % (count+1, self.__class__.materials[count]))
                count += 1
            print("\n")

        self.__class__.materials = sorted(list(set(self.__class__.materials)))

        return {'FINISHED'}

class AMTH_SCENE_OT_cycles_shader_list_nodes_clear(Operator):
    """Clear the list below"""
    bl_idname = "scene.cycles_list_nodes_clear"
    bl_label = "Clear Materials List"

    @classmethod
    def poll(cls, context):
        return cycles_exists

    def execute(self, context):
        AMTH_SCENE_OT_cycles_shader_list_nodes.materials[:] = []
        print("* Cleared Cycles Materials List")
        return {'FINISHED'}

class AMTH_SCENE_OT_amaranth_object_select(Operator):
    '''Select object'''
    bl_idname = "scene.amaranth_object_select"
    bl_label = "Select Object"
    object = bpy.props.StringProperty()
 
    def execute(self, context):
        if self.object:
            object = bpy.data.objects[self.object]

            bpy.ops.object.select_all(action='DESELECT')
            object.select = True
            context.scene.objects.active = object

        return{'FINISHED'}

class AMTH_SCENE_OT_list_missing_node_links(Operator):
    '''Print a list of missing node links'''
    bl_idname = "scene.list_missing_node_links"
    bl_label = "List Missing Node Links"

    count_groups = 0
    count_images = 0
    count_image_node_unlinked = 0

    def execute(self, context):
        missing_groups = []
        missing_images = []
        image_nodes_unlinked = []
        libraries = []
        self.__class__.count_groups = 0
        self.__class__.count_images = 0
        self.__class__.count_image_node_unlinked = 0

        for ma in bpy.data.materials:
            if ma.node_tree:
                for no in ma.node_tree.nodes:
                    if no.type == 'GROUP':
                        if not no.node_tree:
                            self.__class__.count_groups += 1

                            users_ngroup = []

                            for ob in bpy.data.objects:
                                if ob.material_slots and ma.name in ob.material_slots:
                                    users_ngroup.append("%s%s%s" % (
                                        "[L] " if ob.library else "",
                                        "[F] " if ob.use_fake_user else "",
                                        ob.name))

                            missing_groups.append("MA: %s%s%s [%s]%s%s%s\n" % (
                                "[L] " if ma.library else "",
                                "[F] " if ma.use_fake_user else "",
                                ma.name, ma.users,
                                " *** No users *** " if ma.users == 0 else "",
                                "\nLI: %s" % 
                                ma.library.filepath if ma.library else "",
                                "\nOB: %s" % ',  '.join(users_ngroup) if users_ngroup else ""))

                            if ma.library:
                                libraries.append(ma.library.filepath)
                    if no.type == 'TEX_IMAGE':

                        outputs_empty = not no.outputs['Color'].is_linked and not no.outputs['Alpha'].is_linked

                        if no.image:
                            import os.path
                            image_path_exists = os.path.exists(
                                                    bpy.path.abspath(
                                                        no.image.filepath, library=no.image.library))

                        if outputs_empty or not \
                           no.image or not \
                           image_path_exists:

                            users_images = []

                            for ob in bpy.data.objects:
                                if ob.material_slots and ma.name in ob.material_slots:
                                    users_images.append("%s%s%s" % (
                                        "[L] " if ob.library else "",
                                        "[F] " if ob.use_fake_user else "",
                                        ob.name))

                            if outputs_empty:
                                self.__class__.count_image_node_unlinked += 1

                                image_nodes_unlinked.append("%s%s%s%s%s [%s]%s%s%s%s%s\n" % (
                                    "NO: %s" % no.name,
                                    "\nMA: ",
                                    "[L] " if ma.library else "",
                                    "[F] " if ma.use_fake_user else "",
                                    ma.name, ma.users,
                                    " *** No users *** " if ma.users == 0 else "",
                                    "\nLI: %s" % 
                                    ma.library.filepath if ma.library else "",
                                    "\nIM: %s" % no.image.name if no.image else "",
                                    "\nLI: %s" % no.image.filepath if no.image and no.image.filepath else "",
                                    "\nOB: %s" % ',  '.join(users_images) if users_images else ""))
                            

                            if not no.image or not image_path_exists:
                                self.__class__.count_images += 1

                                missing_images.append("MA: %s%s%s [%s]%s%s%s%s%s\n" % (
                                    "[L] " if ma.library else "",
                                    "[F] " if ma.use_fake_user else "",
                                    ma.name, ma.users,
                                    " *** No users *** " if ma.users == 0 else "",
                                    "\nLI: %s" % 
                                    ma.library.filepath if ma.library else "",
                                    "\nIM: %s" % no.image.name if no.image else "",
                                    "\nLI: %s" % no.image.filepath if no.image and no.image.filepath else "",
                                    "\nOB: %s" % ',  '.join(users_images) if users_images else ""))

                                if ma.library:
                                    libraries.append(ma.library.filepath)

        # Remove duplicates and sort
        missing_groups = sorted(list(set(missing_groups)))
        missing_images = sorted(list(set(missing_images)))
        image_nodes_unlinked = sorted(list(set(image_nodes_unlinked)))
        libraries = sorted(list(set(libraries)))

        print("\n\n== %s missing image %s, %s missing node %s and %s image %s unlinked ==" %
            ("No" if self.__class__.count_images == 0 else str(self.__class__.count_images),
            "node" if self.__class__.count_images == 1 else "nodes",
            "no" if self.__class__.count_groups == 0 else str(self.__class__.count_groups),
            "group" if self.__class__.count_groups == 1 else "groups",
            "no" if self.__class__.count_image_node_unlinked == 0 else str(self.__class__.count_image_node_unlinked),
            "node" if self.__class__.count_groups == 1 else "nodes"))

        # List Missing Node Groups
        if missing_groups:
            print("\n* Missing Node Group Links\n")
            for mig in missing_groups:
                print(mig)

        # List Missing Image Nodes
        if missing_images:
            print("\n* Missing Image Nodes Link\n")

            for mii in missing_images:
                print(mii)

        # List Image Nodes with its outputs unlinked
        if image_nodes_unlinked:
            print("\n* Image Nodes Unlinked\n")

            for nou in image_nodes_unlinked:
                print(nou)

        if missing_groups or \
           missing_images or \
           image_nodes_unlinked:
            if libraries:
                print("\nThat's bad, run check on %s:" % (
                    "this library" if len(libraries) == 1 else "these libraries"))
                for li in libraries:
                    print(li)
        else:
            self.report({"INFO"}, "Yay! No missing node links")            

        print("\n")

        if missing_groups and missing_images:
            self.report({"WARNING"}, "%d missing image %s and %d missing node %s found" %
                (self.__class__.count_images, "node" if self.__class__.count_images == 1 else "nodes",
                self.__class__.count_groups, "group" if self.__class__.count_groups == 1 else "groups"))

        return{'FINISHED'}

class AMTH_SCENE_OT_list_missing_material_slots(Operator):
    '''List objects with empty material slots'''
    bl_idname = "scene.list_missing_material_slots"
    bl_label = "List Empty Material Slots"

    objects = []
    libraries = []

    def execute(self, context):
        self.__class__.objects = []
        self.__class__.libraries = []

        for ob in bpy.data.objects:
            for ma in ob.material_slots:
                if not ma.material:
                    self.__class__.objects.append('%s%s' % (
                        '[L] ' if ob.library else '',
                        ob.name))
                    if ob.library:
                        self.__class__.libraries.append(ob.library.filepath)

        self.__class__.objects = sorted(list(set(self.__class__.objects)))
        self.__class__.libraries = sorted(list(set(self.__class__.libraries)))

        if len(self.__class__.objects) == 0:
            self.report({"INFO"}, "No objects with empty material slots found")
        else:
            print("\n* A total of %d %s with empty material slots was found \n" % (
                    len(self.__class__.objects),
                    "object" if len(self.__class__.objects) == 1 else "objects"))

            count = 0
            count_lib = 0

            for obs in self.__class__.objects:
                print('%02d. %s' % (
                    count+1, self.__class__.objects[count]))
                count += 1

            if self.__class__.libraries:
                print("\n\n* Check %s:\n" % 
                    ("this library" if len(self.__class__.libraries) == 1
                        else "these libraries"))

                for libs in self.__class__.libraries:
                    print('%02d. %s' % (
                        count_lib+1, self.__class__.libraries[count_lib]))
                    count_lib += 1
            print("\n")

        return{'FINISHED'}

class AMTH_SCENE_OT_list_missing_material_slots_clear(Operator):
    """Clear the list below"""
    bl_idname = "scene.list_missing_material_slots_clear"
    bl_label = "Clear Empty Material Slots List"
    
    def execute(self, context):
        AMTH_SCENE_OT_list_missing_material_slots.objects[:] = []
        print("* Cleared Empty Material Slots List")
        return {'FINISHED'}

class AMTH_SCENE_OT_blender_instance_open(Operator):
    '''Open in a new Blender instance'''
    bl_idname = "scene.blender_instance_open"
    bl_label = "Open Blender Instance"
    filepath = bpy.props.StringProperty()

    def execute(self, context):
        if self.filepath:
            import os.path
            filepath = os.path.normpath(bpy.path.abspath(self.filepath))

            import subprocess
            try:
                subprocess.Popen([bpy.app.binary_path, filepath])
            except:
                print("Error on the new Blender instance")
                import traceback
                traceback.print_exc()

        return{'FINISHED'}

class AMTH_SCENE_PT_scene_debug(Panel):
    '''Scene Debug'''
    bl_label = 'Scene Debug'
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon="RADIO")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        objects =  bpy.data.objects
        ob_act = context.active_object
        images = bpy.data.images
        lamps = bpy.data.lamps
        images_missing = []
        list_missing_images = scene.amaranth_debug_scene_list_missing_images
        materials = AMTH_SCENE_OT_cycles_shader_list_nodes.materials
        materials_count = len(AMTH_SCENE_OT_cycles_shader_list_nodes.materials)
        missing_material_slots_obs = AMTH_SCENE_OT_list_missing_material_slots.objects
        missing_material_slots_count = len(AMTH_SCENE_OT_list_missing_material_slots.objects)
        missing_material_slots_lib = AMTH_SCENE_OT_list_missing_material_slots.libraries
        engine = scene.render.engine

        # List Missing Images
        box = layout.box()
        row = box.row(align=True)
        split = row.split()
        col = split.column()

        if images:
            import os.path

            for im in images:
                if im.type not in ['UV_TEST', 'RENDER_RESULT', 'COMPOSITING']: 
                    if not os.path.exists(bpy.path.abspath(im.filepath, library=im.library)):
                        images_missing.append(["%s%s [%s]%s" % (
                            '[L] ' if im.library else '',
                            im.name, im.users,
                            ' [F]' if im.use_fake_user else ''),
                            im.filepath if im.filepath else 'No Filepath',
                            im.library.filepath if im.library else ''])

            if images_missing:
                row = col.row(align=True)
                row.alignment = 'LEFT'
                row.prop(scene, 'amaranth_debug_scene_list_missing_images',
                            icon="%s" % 'TRIA_DOWN' if list_missing_images else 'TRIA_RIGHT',
                            emboss=False)

                split = split.split()
                col = split.column()

                col.label(text="%s missing %s" % (
                             str(len(images_missing)),
                             'image' if len(images_missing) == 1 else 'images'),
                             icon="ERROR")

                if list_missing_images:
                    col = box.column(align=True)
                    for mis in images_missing:
                        col.label(text=mis[0],
                         icon="IMAGE_DATA")
                        col.label(text=mis[1], icon="LIBRARY_DATA_DIRECT")
                        if mis[2]:
                            row = col.row(align=True)
                            row.alignment = "LEFT"
                            row.operator(AMTH_SCENE_OT_blender_instance_open.bl_idname,
                                         text=mis[2],
                                         icon="LINK_BLEND",
                                         emboss=False).filepath=mis[2]
                        col.separator()
            else:
                row = col.row(align=True)
                row.alignment = 'LEFT'
                row.label(text="Great! No missing images", icon="RIGHTARROW_THIN")

                split = split.split()
                col = split.column()

                col.label(text="%s %s loading correctly" % (
                             str(len(images)),
                             'image' if len(images) == 1 else 'images'),
                             icon="IMAGE_DATA")
        else:
            row = col.row(align=True)
            row.alignment = 'LEFT'
            row.label(text="No images loaded yet", icon="RIGHTARROW_THIN")

        # List Cycles Materials by Shader
        if cycles_exists and engine == 'CYCLES':
            box = layout.box()
            split = box.split()
            col = split.column(align=True)
            col.prop(scene, 'amaranth_cycles_node_types',
                icon="MATERIAL")

            row = split.row(align=True)
            row.operator(AMTH_SCENE_OT_cycles_shader_list_nodes.bl_idname,
                            icon="SORTSIZE",
                            text="List Materials Using Shader")
            if materials_count != 0: 
                row.operator(AMTH_SCENE_OT_cycles_shader_list_nodes_clear.bl_idname,
                                icon="X", text="")
            col.separator()

            try:
                materials
            except NameError:
                pass
            else:
                if materials_count != 0: 
                    col = box.column(align=True)
                    count = 0
                    col.label(text="%s %s found" % (materials_count,
                        'material' if materials_count == 1 else 'materials'), icon="INFO")
                    for mat in materials:
                        count += 1
                        col.label(text='%s' % (materials[count-1]), icon="MATERIAL")

        # List Missing Node Trees
        box = layout.box()
        row = box.row(align=True)
        split = row.split()
        col = split.column(align=True)

        split = col.split()
        split.label(text="Node Links")
        split.operator(AMTH_SCENE_OT_list_missing_node_links.bl_idname,
                        icon="NODETREE")

        if AMTH_SCENE_OT_list_missing_node_links.count_groups != 0 or \
            AMTH_SCENE_OT_list_missing_node_links.count_images != 0 or \
            AMTH_SCENE_OT_list_missing_node_links.count_image_node_unlinked != 0:
            col.label(text="Warning! Check Console", icon="ERROR")

        if AMTH_SCENE_OT_list_missing_node_links.count_groups != 0:
            col.label(text="%s" % ("%s node %s missing link" % (
                     str(AMTH_SCENE_OT_list_missing_node_links.count_groups),
                     "group" if AMTH_SCENE_OT_list_missing_node_links.count_groups == 1 else "groups")),
                     icon="NODETREE")
        if AMTH_SCENE_OT_list_missing_node_links.count_images != 0:
            col.label(text="%s" % ("%s image %s missing link" % (
                     str(AMTH_SCENE_OT_list_missing_node_links.count_images),
                     "node" if AMTH_SCENE_OT_list_missing_node_links.count_images == 1 else "nodes")),
                     icon="IMAGE_DATA")

        if AMTH_SCENE_OT_list_missing_node_links.count_image_node_unlinked != 0:
            col.label(text="%s" % ("%s image %s with no output conected" % (
                     str(AMTH_SCENE_OT_list_missing_node_links.count_image_node_unlinked),
                     "node" if AMTH_SCENE_OT_list_missing_node_links.count_image_node_unlinked == 1 else "nodes")),
                     icon="NODE")

        # List Empty Materials Slots
        box = layout.box()
        split = box.split()
        col = split.column(align=True)
        col.label(text="Material Slots")

        row = split.row(align=True)
        row.operator(AMTH_SCENE_OT_list_missing_material_slots.bl_idname,
                        icon="MATERIAL",
                        text="List Empty Materials Slots")
        if missing_material_slots_count != 0: 
            row.operator(AMTH_SCENE_OT_list_missing_material_slots_clear.bl_idname,
                            icon="X", text="")
        col.separator()

        try:
            missing_material_slots_obs
        except NameError:
            pass
        else:
            if missing_material_slots_count != 0: 
                col = box.column(align=True)
                count = 0
                count_lib = 0
                col.label(text="%s %s with empty material slots found" % (
                    missing_material_slots_count,
                    'object' if missing_material_slots_count == 1 else 'objects'),
                    icon="INFO")

                for obs in missing_material_slots_obs:
                    count += 1

                    row = col.row()
                    row.alignment = 'LEFT'
                    row.label(text='%s' % missing_material_slots_obs[count-1],
                                icon="OBJECT_DATA")

                if missing_material_slots_lib:
                    col.separator()
                    col.label("Check %s:" % (
                        "this library" if
                            len(missing_material_slots_lib) == 1
                                else "these libraries"))
                    
                    for libs in missing_material_slots_lib:
                        count_lib += 1
                        row = col.row(align=True)
                        row.alignment = "LEFT"
                        row.operator(AMTH_SCENE_OT_blender_instance_open.bl_idname,
                                     text=missing_material_slots_lib[count_lib-1],
                                     icon="LINK_BLEND",
                                     emboss=False).filepath=missing_material_slots_lib[count_lib-1]

# // FEATURE: Scene Debug