''' Replaces the default shape key panel with a Blabels panel.

Adds the ability to sort shape keys by labels, in addition to a number
of other shape key related operations.'''

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
from mathutils import Vector
from bpy.types import Panel
from .blabels import *


class Shape_Key_Blabels(Blabels):
    @property
    def name(self):
        return 'shape_key'

    @property
    def labels(self):
        return self.context.object.data.shape_key_labels

    @property
    def labels_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the labels prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        return {'attr': 'shape_key_labels',
                'source': self.context.object.data,
                'prop': bpy.types.Mesh.shape_key_labels}

    @property
    def selected_items_prop(self):
        return self.context.object.selected_shape_keys

    @property
    def selected_items_prop_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the selected label items prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        return {'attr': 'selected_shape_keys',
                'source': self.context.object,
                'prop': bpy.types.Object.selected_shape_keys}

    @property
    def active_label_index(self):
        return self.context.object.active_shape_key_label_index

    @active_label_index.setter
    def active_label_index(self, index):
        self.context.object.active_shape_key_label_index = index

    @property
    def active_label_index_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the active label index prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        return {'attr': 'active_shape_key_label_index',
                'source': self.context.object,
                'prop': bpy.types.Object.active_shape_key_label_index}

    @property
    def active_item_index(self):
        return self.context.object.active_shape_key_index

    @active_item_index.setter
    def active_item_index(self, index):
        self.context.object.active_shape_key_index = index

    @property
    def items(self):
        obj = self.context.object
        if obj.data.shape_keys:
            return [item for item in obj.data.shape_keys.key_blocks]
        else:
            return []

    @property
    def view_mode(self):
        return self.context.scene.shape_keys_view_mode

    @view_mode.setter
    def view_mode(self, mode):
        context.scene.shape_keys_view_mode = mode.upper()

    def view_mode_items(self):
        '''Options that view mode can be set to.'''
        return [item[1] for item in bpy.types.Scene.shape_keys_view_mode[1]['items']]

    def add_item_orig(self, **add_item_kwargs):
        # add_item_kwargs: from_mix = self.from_mix
        bpy.ops.object.shape_key_add(**add_item_kwargs)

    def remove_item_orig(self, **remove_item_kwargs):
        bpy.ops.object.shape_key_remove(**remove_item_kwargs)

    def move_item_orig(self, **move_item_kwargs):
        # move_item_kwargs: type = self.type
        if 'direction' in move_item_kwargs:
            move_item_kwargs['type'] = move_item_kwargs.pop('direction')
        bpy.ops.object.shape_key_move(**move_item_kwargs)

    def filter_view_mode(self, indexes):
        indexes = super().filter_view_mode(indexes)

        # Filter "ALL" label by view mode
        view_mode = self.view_mode.lower()
        items = self.items
        if view_mode == 'visible':
            indexes = [i for i in indexes if not items[i].mute]
        elif view_mode == 'hidden':
            indexes = [i for i in indexes if items[i].mute]

        return indexes

    def toggle_visible_item(self, inverse=False):
        items = self.visible_items
        if inverse:
            # Hide or show all
            if any(1 for item in items if item.mute):
                for item in items:
                    item.mute = False
            else:
                for item in items:
                    item.mute = True
        else:
            # Inverse Visible
            for item in items:
                item.mute = not item.mute


class ShapeKeyOperators(BlabelOperators):
    def __init__(self, blabel_class=None, base_name=None):
        if blabel_class is None:
            blabel_class = Shape_Key_Blabels
        super().__init__(blabel_class, base_name)

    @ui_object
    def item_toggle_visibility(self):
        shift = bpy.props.BoolProperty(default=False)

        def invoke_func(opr_self, context, event):
            opr_self.shift = event.shift

        operator = self.blabel_operator(
            blabel_name="toggle_visible",
            label="Toggle Visibility on Item",
            execute_func=lambda opr_self, context: self.bl_class(context).toggle_visible_item(inverse=not opr_self.shift),
            invoke_func=invoke_func,
            members={'shift': shift},
            test_items=True)

        return operator

    @ui_object
    def item_add(self):
        from_mix = bpy.props.BoolProperty(
            name="Add To Label From Mix",
            default=False)

        operator = self.blabel_operator(
            blabel_name="add_to_label",
            label="Add Item",
            execute_func=lambda opr_self, context: self.bl_class(context).add_item(from_mix=opr_self.from_mix),
            members={'from_mix': from_mix})
        return operator

    @property
    def view_mode_items(self):
        items = super().view_mode_items
        items.extend([
                      ('Visible', "Visible", "View Visible Shape Keys"),
                      ('Hidden', "Hidden", "View Hidden Shape Keys"),
                     ])
        return items

    @ui_object
    def view_mode_prop(self):
        bpy.types.Scene.shape_keys_view_mode = bpy.props.EnumProperty(
            name="View",
            items = self.view_mode_items)
        return BlabelUIObject(bpy.types.Scene.shape_keys_view_mode, 'bpy.types.Scene.shape_keys_view_mode')

    ####################################################################
    #                   Non-Essential Operators

    @ui_object
    def create_corrective(self):
        operator = self.blabel_operator(
            blabel_name="create_corrective",
            label="Create Corrective Driver",
            description="Create Corrective Driver from Selection",
            execute_func=lambda opr_self, context: create_corrective_driver(context=context),
            test_items=True)
        return operator

    @ui_object
    def scrub_two_keys(self):
        percent = bpy.props.FloatProperty(
            name="Percent",
            default=0.5,
            soft_min=0,
            soft_max=1,
            subtype='FACTOR')

        def execute(opr_self, context):
            # Get indexes of visible keys
            label_accessor = self.bl_class(context)
            selected = label_accessor.selected_item_indexes

            if len(selected) == 2:
                shape_keys = label_accessor.items
                shape_keys[selected[0]].value = opr_self.percent
                shape_keys[selected[1]].value = 1.0 - opr_self.percent

        operator = self.blabel_operator(
            blabel_name="scrub_two",
            label="Scrub Between Two Shape Keys",
            execute_func=execute,
            test_items=True,
            members={'percent': percent})
        return operator

    @ui_object
    def deform_axis(self):
        deform_axis = bpy.props.FloatVectorProperty(
            name="Deform Axis",
            description="",
            default=(1, 1, 1),
            soft_min=0,
            soft_max=1,
            subtype='XYZ')

        invoked = False
        selected = []
        offsets = []

        def execute(opr_self, context):
            obj = context.active_object
            label_accessor = self.bl_class(context)
            shape_keys = label_accessor.items

            if opr_self.invoked:
                opr_self.selected = label_accessor.selected_item_indexes

            selected = [label_accessor.items[i] for i in opr_self.selected]

            # Initialize
            if opr_self.invoked:
                # Get offsets
                opr_self.offsets = []
                for shape_key in selected:
                    offset_key = []
                    for x in range(len(shape_key.data)):
                        offset = shape_key.data[x].co - shape_key.relative_key.data[x].co
                        if offset != 0.0:
                            offset_key.append((x, offset))
                    opr_self.offsets.append(offset_key)

            # Apply offsets
            for i, shape_key in enumerate(selected):
                if shape_key.relative_key:
                    for x, offset in opr_self.offsets[i]:
                        shape_key.data[x].co = shape_key.relative_key.data[x].co + inline_vector_mult(offset, opr_self.deform_axis)

            obj.data.update()
            opr_self.invoked = False

        def invoke(opr_self, context, event):
            opr_self.invoked = True

        operator = self.blabel_operator(
            blabel_name="axis",
            label="Limit Axis",
            description="Limit Shape Key Deformation by Axis",
            execute_func=execute,
            invoke_func=invoke,
            test_items=True,
            members={'deform_axis': deform_axis,
                     'invoked': invoked,
                     'selected': selected,
                     'offsets': offsets})
        return operator

    @ui_object
    def copy_into(self):
        operator = self.blabel_operator(
            blabel_name="copy_into",
            label="Copy Into",
            description="Replace the active selected shape with the sum of the other selected shapes.",
            execute_func=lambda opr_self, context: copy_into(context=context),
            test_items=True)
        return operator

    @ui_object
    def negate(self):
        selected = bpy.props.BoolProperty(default=True, description="Negate Weight of Visible")

        def invoke(opr_self, context, event):
            opr_self.selected = not event.shift

        operator = self.blabel_operator(
            blabel_name="negate",
            label="Negate Weight of Selected",
            execute_func=lambda opr_self, context: negate_shape_key(context=context, use_selected=opr_self.selected),
            invoke_func=invoke,
            members={'selected': selected},
            test_items=True)
        return operator

    @ui_object
    def toggle_visibility(self):

        shift = bpy.props.BoolProperty(default=True, description="Rotate Visible in Selection")

        def invoke(opr_self, context, event):
            opr_self.shift = event.shift

        operator = self.blabel_operator(
            blabel_name="toggle_visibility",
            label="Inverse Visibility of Selected",
            execute_func=lambda opr_self, context: toggle_visibility(context=context, rotate_toggle=opr_self.shift),
            invoke_func=invoke,
            members={'shift': shift},
            test_items=True)
        return operator

    @ui_object
    def copy(self):
        mirror = bpy.props.BoolProperty(default=False, description="Create Mirror from Selected Shape Keys")
        selected = bpy.props.BoolProperty(default=True, description="Create New Shape Key from Visible")
        absolute = bpy.props.BoolProperty(default=False, description="Copy Shape Key at a value of 1.")

        def invoke(opr_self, context, event):
            opr_self.selected = not event.shift
            opr_self.absolute = event.ctrl

        def execute(opr_self, context):
            copy(context=context, mirror=opr_self.mirror, selected=opr_self.selected, absolute=opr_self.absolute)

        operator = self.blabel_operator(
            blabel_name="copy",
            label="Create New Shape Key from Selected",
            execute_func=execute,
            invoke_func=invoke,
            members={'mirror': mirror, 'selected': selected, 'absolute': absolute},
            test_items=True)

        return operator


shape_key_operators = ShapeKeyOperators()


'''----------------------------------------------------------------------------
                            Shape Key Operators
----------------------------------------------------------------------------'''


def inline_vector_mult(vectorA, vectorB):
    '''Multiply each index of two vectors by each other,
    so [vectorA[0] * vectorB[0], ...] '''
    return Vector([i * j for i, j in zip(vectorA, vectorB)])


def shape_keys_mute_others(shape_keys, selected_keys):
    '''Hide other shape keys and return their original states'''

    muted_states = []
    for key in shape_keys:
        muted_states.append(key.mute)
        if key in selected_keys:
            key.mute = False
        else:
            key.mute = True
    return muted_states


def shape_keys_restore_muted(shape_keys, muted_states):
    '''Restore muted state'''
    for x, key in enumerate(shape_keys):
        key.mute = muted_states[x]


def create_corrective_driver(context=None):
    if context is None:
        context = bpy.context

    obj = context.active_object
    mesh = obj.data
    active = obj.active_shape_key_index
    sel = Shape_Key_Blabels(context).selected_item_indexes
    sel.sort()
    if active not in sel:
        active = sel.pop(-1)
    else:
        sel.remove(active)
    keys = mesh.shape_keys
    driver_path = 'key_blocks["%s"].value' % keys.key_blocks[active].name

    # Create Driver
    keys.driver_remove(driver_path)
    fcurve = keys.driver_add(driver_path)

    # Setup Driver
    drv = fcurve.driver
    drv.type = 'MIN'

    for i in sel:
        var = drv.variables.new()
        var.name = keys.key_blocks[i].name
        var.targets[0].id_type = 'MESH'
        var.targets[0].id = mesh
        var.targets[0].data_path = 'shape_keys.key_blocks["%s"].value' % var.name


def toggle_visibility(context=None, rotate_toggle=False):
    selected = Shape_Key_Blabels(context).selected_items

    if selected:
        if not rotate_toggle or len(selected) == 1:
            # Inverse Selected Visible
            for shape_key in selected:
                shape_key.mute = not shape_key.mute
        else:
            # Rotate Selected Visible
            vis = [x for x, shape_key in enumerate(selected) if not shape_key.mute]
            if len(vis) != 1:
                # Initialize rotations
                for shape_key in selected:
                    shape_key.mute = 1
                selected[0].mute = 0
            else:
                vis = vis[0]
                selected[vis].mute = True
                selected[(vis + 1) % len(selected)].mute = False


def negate_shape_key(context=None, use_selected=True):
    if context is None:
        context = bpy.context

    # Operate on selected
    if use_selected:
        shape_keys = Shape_Key_Blabels(context).selected_items
    else:
        shape_keys = Shape_Key_Blabels(context).visible_items

    # Inverse Weights
    for shape_key in shape_keys:
        if shape_key.value >= 0:
            shape_key.slider_min = -1.0
            shape_key.value = -1.0
        else:
            shape_key.slider_min = 0.0
            shape_key.value = 1


def copy_into(context=None):
    '''Replaces the active selected shape with the sum of the other
    selected shapes '''

    if context is None:
        context = bpy.context

    label_accessor = Shape_Key_Blabels(context)
    active_item = label_accessor.active_item
    selected = label_accessor.get_visible_items()[-1]

    if active_item in selected:
        selected.remove(active_item)

    for x in range(len(active_item.data)):
        deltas = Vector([0.0, 0.0, 0.0])
        for shape_key in selected:
            deltas += shape_key.relative_key.data[x].co - shape_key.data[x].co
        active_item.data[x].co = active_item.relative_key.data[x].co - deltas



def copy(context=None, mirror=False, selected=True, absolute=False):
    if context is None:
        context = bpy.context

    # Data gathering
    blabel = Shape_Key_Blabels(context)
    original_item = blabel.active_item
    visible_items = blabel.visible_items
    visible_selected = blabel.selected_items

    if not selected:
        # Do add_to_label, with from mix = True
        bpy.ops.object.shape_key_add_to_label(from_mix=not absolute)
    else:
        # Hide other shape keys and save their states
        muted_states = shape_keys_mute_others(blabel.items, visible_selected)
        muted_states.append(False)

        # Copy
        bpy.ops.object.shape_key_add_to_label(from_mix=not absolute)

        # Restore states
        shape_keys_restore_muted(blabel.items, muted_states)

    new_shape = blabel.active_item
    if absolute:
        # Copy Absolute (copy the shape as if it were at a value of 1)
        if selected:
            copy_items = visible_selected
        else:
            copy_items = [item for item in visible_items if not item.mute]

        for shape_key in copy_items:
            for x, new_shape_data in enumerate(new_shape.data):
                new_shape_data.co += shape_key.data[x].co - shape_key.relative_key.data[x].co

    if mirror:
        bpy.ops.object.shape_key_mirror()

    if len(visible_items) == 1 or (len(visible_selected) == 1 and selected):
        # Copy from original
        new_shape.value = 1.0
        name = original_item.name

    else:
        # Turn on
        new_shape.value = 1.0
        new_shape.mute = False
        name = 'New Key'

    if mirror:
        new_shape.name = name + " Mirrored"
    elif not selected:
        new_shape.name = name + " Copy"


'''----------------------------------------------------------------------------
                            Shape Key Panel
----------------------------------------------------------------------------'''


class ShapeKeyLabelList(BlabelLabelList):
    def __init__(self, context, layout, blabel=None, operators=None, name='Labels'):
        if operators is None:
            operators = shape_key_operators
        if blabel is None:
            blabel = Shape_Key_Blabels
        super().__init__(context, layout, blabel, operators, name)


class ShapeKeyItemList(BlabelItemList):
    def __init__(self, context, layout, blabel=None, operators=None, name=None):
        if name is None:
            name = 'Shape Keys'
        if operators is None:
            operators = shape_key_operators
        if blabel is None:
            blabel = Shape_Key_Blabels
        super().__init__(context, layout, blabel, operators, name)

    @prepost_calls
    def draw_sidebar_top(self):
        self.num_top_sidebar_items += 1
        self.layouts['sidebar'].operator(self.operators.item_add, icon='ZOOMIN', text="").from_mix = False

        if self.items:
            self.layouts['sidebar'].operator(self.operators.item_remove, icon='ZOOMOUT', text="")
            self.layouts['sidebar'].operator(self.operators.item_delete, icon='PANEL_CLOSE', text="")
            self.layouts['sidebar'].operator(self.operators.toggle_visibility, icon='RESTRICT_VIEW_OFF', text='')
            self.layouts['sidebar'].operator(self.operators.copy, icon='PASTEDOWN', text='').mirror = False
            self.layouts['sidebar'].operator(self.operators.copy, icon='ARROW_LEFTRIGHT', text='').mirror = True
            self.layouts['sidebar'].operator(self.operators.negate, icon='FORCE_CHARGE', text='')
            self.num_top_sidebar_items += 6

        self.layouts['sidebar'].menu("MESH_MT_shape_key_specials", icon='DOWNARROW_HLT', text="")
        self.num_top_sidebar_items += 1

    def _post_draw_items(self):
        if self.items:
            bottom = self.layouts['items_column'].row()
            bottom = bottom.split(percentage=0.09, align=True)
            bottom.operator(self.operators.item_toggle_select, icon='PROP_ON', text='')

            bottom = bottom.split(percentage=0.91, align=True)
            bottom.operator(self.operators.null, icon='BLANK1', emboss=False)

            bottom.operator(self.operators.item_toggle_visibility, icon='VISIBLE_IPO_ON', text='')  # .absolute=True
            self.layouts['items_bottom'] = bottom

    @prepost_calls
    def draw_item(self, item):
        super().draw_item(item)
        layouts = self.layouts

        item_row = layouts['item_row']
        item_row.prop(item, 'name', text='')
        item_row = item_row.split(percentage=0.81)
        item_row.prop(item, 'value', text='')
        item_row = item_row.split()
        item_row.prop(item, 'mute', text='')

        layouts['item_row'] = item_row


class DATA_PT_shape_keys(MeshButtonsPanel, Panel):
    bl_label = "Shape Keys"

    @classmethod
    def poll(cls, context):
        return shape_key_operators.poll(context)

    def draw(self, context):
        label_list = ShapeKeyLabelList(context, self.layout)
        item_list = ShapeKeyItemList(context, self.layout)

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
            key = ob.data.shape_keys

            enable_edit = ob.mode != 'EDIT'
            enable_edit_value = False

            if ob.show_only_shape_key is False:
                if enable_edit or (ob.type == 'MESH' and ob.use_shape_key_edit_mode):
                    enable_edit_value = True

            split = layout.split()
            row = split.row()
            row.enabled = enable_edit
            row.prop(key, "use_relative")

            row = split.row()
            row.alignment = 'RIGHT'

            sub = row.row(align=True)
            sub.label()  # XXX, for alignment only
            subsub = sub.row(align=True)
            subsub.active = enable_edit_value
            subsub.prop(ob, "show_only_shape_key", text="")
            sub.prop(ob, "use_shape_key_edit_mode", text="")


            sub = row.row()
            if key.use_relative:
                sub.operator("object.shape_key_clear", icon='X', text="")
            else:
                sub.operator("object.shape_key_retime", icon='RECOVER_LAST', text="")

            if key.use_relative:
                if ob.active_shape_key_index != 0:
                    row = layout.row()
                    row.active = enable_edit_value
                    row.prop(blabel.active_item, 'value')

                    split = layout.split()

                    col = split.column(align=True)
                    col.active = enable_edit_value
                    col.label(text="Range:")
                    col.prop(blabel.active_item, 'slider_min', text="Min")
                    col.prop(blabel.active_item, 'slider_max', text="Max")

                    col = split.column(align=True)
                    col.active = enable_edit_value
                    col.label(text="Blend:")
                    col.prop_search(blabel.active_item, 'vertex_group', ob, 'vertex_groups', text='')
                    col.prop_search(blabel.active_item, 'relative_key', key, 'key_blocks', text='')

            else:
                layout.prop(kb, "interpolation")
                row = layout.column()
                row.active = enable_edit_value
                row.prop(key, 'eval_time')
                row.prop(key, 'slurph')


old_shape_key_menu = None


def label_index_updated(self, context):
    Shape_Key_Blabels(context).label_index_updated()


def shape_key_specials(self, context):
    # Should add this to BlabelOperators so that a menu is part of a blabel.

    self.layout.operator(
        shape_key_operators.create_corrective,
        icon='LINK_AREA')

    self.layout.operator(shape_key_operators.scrub_two_keys, icon='IPO')
    self.layout.operator(shape_key_operators.deform_axis, icon='MANIPUL')
    self.layout.operator(shape_key_operators.copy_into, icon='EXPORT')  # EXPORT, SCREEN_BACK


def register():
    # Add rna for Mesh object, to store label names and corresponding indexes.
    bpy.types.Mesh.shape_key_labels = bpy.props.CollectionProperty(type=IndexCollection)
    bpy.types.Object.selected_shape_keys = bpy.props.CollectionProperty(type=IndexProperty)
    bpy.types.Object.active_shape_key_label_index = bpy.props.IntProperty(default=0, update=label_index_updated)

    # Replace shapekeys panel with my own
    global old_shape_key_menu
    old_shape_key_menu = bpy.types.DATA_PT_shape_keys

    # I wish I knew how to extend existing operators like object.shape_key_move
    # So I could override those with mine, and not risk my label state machine
    # becoming invalid if some other script/user calls object.shape_key_move
    # instead of object.shape_key_move_to_label

    shape_key_operators.register()

    bpy.types.MESH_MT_shape_key_specials.append(shape_key_specials)


def unregister():
    # bpy.utils.unregister_module(__name__)
    bpy.utils.register_class(old_shape_key_menu)
    bpy.types.MESH_MT_shape_key_specials.remove(shape_key_specials)
    shape_key_operators.unregister()
    del bpy.types.Scene.shape_keys_view_mode

    # Should I delete the rna types created?  Hmmmm.
    # I don't want a user to lose data from reloading my addon,
    # but I also don't want extra data saved if it's permanently disabled.
    # I think the lesser evil here is not to delete data.

if __name__ == "__main__":
    register()
