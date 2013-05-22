''' Replaces the default vertex group panel with a Blabels panel.

Adds the ability to sort vertex groups by labels.  Additional features may
be forthcoming.'''

'''
*******************************************************************************
    License and Copyright
    Copyright 2012-2013 Jordan Hueckstaedt
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import bpy
from bpy.types import Panel
from .blabels import *


class Vertex_Group_Blabels(Blabels):
    @property
    def name(self):
        return 'vertex_groups'

    @property
    def labels(self):
        return self.context.object.vertex_group_labels

    @property
    def labels_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the labels prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        return {'attr': 'vertex_group_labels',
                'source': self.context.object,
                'prop': bpy.types.Object.vertex_group_labels}

    @property
    def selected_items_prop(self):
        return self.context.object.selected_vertex_group

    @property
    def selected_items_prop_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the selected label items prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        return {'attr': 'selected_vertex_group',
                'source': self.context.object,
                'prop': bpy.types.Object.selected_vertex_group}

    @property
    def active_label_index(self):
        return self.context.object.active_vertex_group_label_index

    @active_label_index.setter
    def active_label_index(self, index):
        self.context.object.active_vertex_group_label_index = index

    @property
    def active_label_index_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the active label index prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        return {'attr': 'active_vertex_group_label_index',
                'source': self.context.object,
                'prop': bpy.types.Object.active_vertex_group_label_index}

    @property
    def active_item_index(self):
        return self.context.object.vertex_groups.active_index

    @active_item_index.setter
    def active_item_index(self, index):
        self.context.object.vertex_groups.active_index = index

    @property
    def items(self):
        return [item for item in self.context.object.vertex_groups]

    @property
    def view_mode(self):
        return self.context.scene.vertex_group_view_mode

    @view_mode.setter
    def view_mode(self, mode):
        context.scene.vertex_group_view_mode = mode.upper()

    def add_item_orig(self, **add_item_kwargs):
        # I don't believe vertex groups have an optional parameter here yet.
        bpy.ops.object.vertex_group_add(**add_item_kwargs)

    def remove_item_orig(self, **remove_item_kwargs):
        bpy.ops.object.vertex_group_remove(**remove_item_kwargs)

    def move_item_orig(self, **move_item_kwargs):
        # move_item_kwargs: type = self.type
        bpy.ops.object.vertex_group_move(**move_item_kwargs)

    def get_armature_groups(self):
        obj = self.context.object

        # Find armature group.
        bones = []
        armatures = 0
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.use_vertex_groups and mod.object:
                    bones = [bone.name for bone in mod.object.data.bones]
                    armatures += 1
                    if armatures == 2:
                        break

        # Get bone indexes
        return [group.index for group in obj.vertex_groups if group.name in bones]

    def filter_view_mode(self, indexes):
        indexes = super().filter_view_mode(indexes)

        # Filter "ALL" label by view mode
        view_mode = self.view_mode.lower()
        items = self.items
        if view_mode == 'locked':
            indexes = [i for i in indexes if items[i].lock_weight]
        elif view_mode == 'unlocked':
            indexes = [i for i in indexes if not items[i].lock_weight]
        elif view_mode == 'armature':
            armature_groups = set(self.get_armature_groups())
            indexes = [i for i in indexes if i in armature_groups]
        return indexes

    def toggle_locked_item(self, inverse=False):
        items = self.items
        indexes, selected = self.get_visible_item_indexes()

        if inverse:
            # Hide or show all
            if any(1 for i in indexes if items[i].lock_weight):
                for i in indexes:
                    items[i].lock_weight = False
            else:
                for i in indexes:
                    items[i].lock_weight = True
        else:
            # Inverse Visible
            for i in indexes:
                items[i].lock_weight = not items[i].lock_weight


def get_selected_groups():
    ''' Easy access wrapper for Vertex_Group_Blabels '''
    items = Vertex_Group_Blabels().selected_items_prop
    return [i.index for i in items]


def get_active_group():
    ''' Easy access wrapper for Vertex_Group_Blabels '''
    return Vertex_Group_Blabels().active_item_index


class VertexGroupOperators(BlabelOperators):
    poll_types = ['MESH', 'LATTICE']

    def __init__(self, blabel_class=None, base_name=None):
        if blabel_class is None:
            blabel_class = Vertex_Group_Blabels
        super().__init__(blabel_class, base_name)

    @ui_object
    def item_toggle_lock(self):
        shift = bpy.props.BoolProperty(default=False)

        def invoke_func(opr_self, context, event):
            opr_self.shift = event.shift

        operator = self.blabel_operator(
            blabel_name="toggle_locked",
            label="Toggle Lock on Item",
            execute_func=lambda opr_self, context: self.bl_class(context).toggle_locked_item(inverse=not opr_self.shift),
            invoke_func=invoke_func,
            members={'shift': shift},
            test_items=True)

        return operator

    @property
    def view_mode_items(self):
        items = super().view_mode_items
        items.extend([
                      ('Armature', "Armature", "View Armature Vertex Groups"),
                      ('Locked', "Locked", "View Locked Vertex Groups"),
                      ('Unlocked', "Unlocked", "View Unlocked Vertex Groups"),
                     ])
        return items

    @ui_object
    def view_mode_prop(self):
        bpy.types.Scene.vertex_group_view_mode = bpy.props.EnumProperty(
            name="View",
            items=self.view_mode_items)
        return BlabelUIObject(bpy.types.Scene.vertex_group_view_mode, 'bpy.types.Scene.vertex_group_view_mode')


vertex_group_operators = VertexGroupOperators()


class VertexGroupLabelList(BlabelLabelList):
    def __init__(self, context, layout, blabel=None, operators=None, name='Labels'):
        if operators is None:
            operators = vertex_group_operators
        if blabel is None:
            blabel = Vertex_Group_Blabels
        super().__init__(context, layout, blabel, operators, name)


class VertexGroupItemList(BlabelItemList):
    def __init__(self, context, layout, blabel=None, operators=None, name=None):
        if name is None:
            name = 'Vertex Groups'
        if operators is None:
            operators = vertex_group_operators
        if blabel is None:
            blabel = Vertex_Group_Blabels
        super().__init__(context, layout, blabel, operators, name)

    @prepost_calls
    def draw_item(self, item):
        super().draw_item(item)
        layouts = self.layouts

        item_row = layouts['item_row']
        item_row = item_row.split(percentage=0.81)
        item_row.prop(item, 'name', text='')
        icon = 'UNLOCKED'
        if item.lock_weight:
            icon = 'LOCKED'
        item_row.prop(item, 'lock_weight', icon=icon, text='')

        layouts['item_row'] = item_row

    def _post_draw_items(self):
        if self.items:
            bottom = self.layouts['items_column'].row()
            bottom = bottom.split(percentage=0.09, align=True)
            bottom.operator(self.operators.item_toggle_select, icon='PROP_ON', text='')

            bottom = bottom.split(percentage=0.81, align=True)
            bottom.operator(self.operators.null, icon='BLANK1', emboss=False)

            bottom.operator(self.operators.item_toggle_lock, icon='UNLOCKED', text='')  # .absolute=True
            self.layouts['items_bottom'] = bottom

    @prepost_calls
    def draw_sidebar_top(self):
        super().draw_sidebar_top()
        self.num_top_sidebar_items += 1
        self.layouts['sidebar'].menu("MESH_MT_vertex_group_specials", icon='DOWNARROW_HLT', text="")


##################################
##     Main UI

class DATA_PT_vertex_groups(MeshButtonsPanel, Panel):
    bl_label = "Vertex Groups"

    @classmethod
    def poll(cls, context):
        return vertex_group_operators.poll(context)

    def draw(self, context):
        label_list = VertexGroupLabelList(context, self.layout)
        item_list = VertexGroupItemList(context, self.layout)

        label_list.draw()
        item_list.draw()
        blabel = item_list.blabel
        operators = item_list.operators

        ##########################
        # THE REST OF THE DEFAULT INTERFACE
        # (Minus the name field, which I removed)
        if blabel.items:

            ob = context.object
            layout = item_list.layouts['main']
            if ob.vertex_groups and (ob.mode == 'EDIT' or (ob.mode == 'WEIGHT_PAINT' and ob.type == 'MESH' and ob.data.use_paint_mask_vertex)):
                row = layout.row()

                sub = row.row(align=True)
                sub.operator("object.vertex_group_assign", text="Assign").new = False
                sub.operator("object.vertex_group_remove_from", text="Remove")

                sub = row.row(align=True)
                sub.operator("object.vertex_group_select", text="Select")
                sub.operator("object.vertex_group_deselect", text="Deselect")

                layout.prop(context.tool_settings, "vertex_group_weight", text="Weight")



##################################
##     Register UI
def label_index_updated(self, context):
    Vertex_Group_Blabels(context).label_index_updated()

old_vertex_group_menu = None


def register():
    # Add rna for Mesh object, to store label names and corresponding indexes.
    bpy.types.Object.vertex_group_labels = bpy.props.CollectionProperty(type=IndexCollection)
    bpy.types.Object.selected_vertex_group = bpy.props.CollectionProperty(type=IndexProperty)
    bpy.types.Object.active_vertex_group_label_index = bpy.props.IntProperty(default=0)

    # Replace shapekeys panel with my own
    global old_vertex_group_menu
    old_vertex_group_menu = bpy.types.DATA_PT_vertex_groups

    vertex_group_operators.register()


def unregister():
    # bpy.utils.unregister_module(__name__)
    bpy.utils.register_class(old_vertex_group_menu)

    del bpy.types.Scene.vertex_group_view_mode
    vertex_group_operators.unregister()
    # Should I delete the rna types created?  Hmmmm.
    # I don't want a user to lose data from reloading my addon,
    # but I also don't want extra data saved if it's permanently disabled.
    # I think the lesser evil here is not to delete data.

if __name__ == "__main__":
    register()
