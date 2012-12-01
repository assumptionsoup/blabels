''' Replaces the default shape key panel with an "Advanced" one.

Adds the ability to sort shape keys by labels, in addition to a number
of other shape key related operations.'''

'''
*******************************************************************************
	License and Copyright
	Copyright 2012 Jordan Hueckstaedt
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
from bpy.types import Menu, Panel
from advanced_labels import *

bl_info = {
    "name": "Advanced Shapekey Panel",
    "author": "Jordan Hueckstaedt",
    "version": (1, 1),
    "blender": (2, 63, 0),
    "location": "Properties > Shape Keys",
    "warning": "", # used for warning icon and text in addons panel
    "description": "Allows the user to group shape keys into labels.\
	Also adds new functions for manipulating shape keys.",
    "wiki_url": "",
	"tracker_url": "",
	"support": "TESTING",
    "category": "Rigging"
}

class Advanced_Shape_Key_Labels( Advanced_Labels):
	def get_labels( self ):
		return self.context.object.data.shape_key_labels
	
	def get_selected_items( self ):
		return self.context.object.selected_shape_keys
	
	def get_active_index( self ):
		return self.context.object.active_shape_key_label_index
	
	def set_active_index( self, index ):
		self.context.object.active_shape_key_label_index = index
	
	def get_active_item_index( self ):
		return self.context.object.active_shape_key_index
	
	def set_active_item_index( self, index ):
		self.context.object.active_shape_key_index = index
	
	def get_items( self ):
		obj = self.context.object
		if obj.data.shape_keys:
			return obj.data.shape_keys.key_blocks
		else:
			return []
	
	def get_view_mode( self ):
		return self.context.scene.shape_keys_view_mode
	
	def set_view_mode( self, mode ):
		context.scene.shape_keys_view_mode = mode.upper()
	
	def add_item_orig( self, **add_item_kwargs ):
		# add_item_kwargs: from_mix = self.from_mix
		bpy.ops.object.shape_key_add(**add_item_kwargs)
	
	def remove_item_orig( self, **remove_item_kwargs ):
		bpy.ops.object.shape_key_remove( **remove_item_kwargs )
	
	def move_item_orig( self, **move_item_kwargs ):
		# move_item_kwargs: type = self.type
		if 'direction' in move_item_kwargs:
			move_item_kwargs['type'] = move_item_kwargs.pop('direction')
		bpy.ops.object.shape_key_move( **move_item_kwargs )

	def filter_view_mode( self, indexes, selected ):
		# Filter "ALL" label by view mode
		view_mode = self.get_view_mode()
		items = self.get_items()
		if view_mode == 'VISIBLE':
			indexes = [i for i in indexes if not items[i].mute]
			selected = [i for i in selected if i in indexes]
		elif view_mode == 'HIDDEN':
			indexes = [i for i in indexes if items[i].mute]
			selected = [i for i in selected if i in indexes]

		return indexes, selected

	def toggle_visible_item( self, inverse = False ):
		items = self.get_items()
		
		indexes, selected = self.get_visible_item_indexes()
		
		if inverse:
			# Hide or show all
			if any(1 for i in indexes if items[i].mute):
				for i in indexes:
					items[i].mute = False
			else:
				for i in indexes:
					items[i].mute = True
		else:
			# Inverse Visible
			for i in indexes:
				items[i].mute = not items[i].mute

'''----------------------------------------------------------------------------
                            Label Helpers
----------------------------------------------------------------------------'''

def label_poll(context, test_shapes = False, test_mode = True):
	# Simple function for most the poll methods in this module
	obj = context.object
	if not (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and \
		context.scene.render.engine in {'BLENDER_RENDER', 'BLENDER_GAME'}):
		return False

	if test_mode and context.mode == 'EDIT_MESH':
		return False
	
	if test_shapes:
		return obj.data.shape_keys
	
	return True
	
def strip_label_number(label):
	# Remove numbers from label name and return it
	name = label.name
	name = name.split("(")[0]
	return name.strip()
	
def format_label_name(label, num_items = None):
	''' Updates the label name with the number of items in the label if no
	overriding number is given. '''
	name = strip_label_number(label)
	if num_items is None:
		num_items = len(label.indexes)
	label.name = "{:<20}({})".format(name, num_items)

def get_visible_selection(obj, indexes):
	# Get selected
	selected = [i.index for i in obj.selected_shape_keys]
	if not selected:
		selected = [obj.active_shape_key_index]
	selected = set(selected)
	
	return [i for i in indexes if i in selected]

def get_visible_indexes(context, skip_view_mode_filter = False):
	# Get visible shape key indexes
	obj = context.object
	labels = obj.data.shape_key_labels
	index = obj.active_shape_key_label_index
	keys = obj.data.shape_keys
	indexes = []
	
	if index != 0 and labels and len(labels):
		# Invalid State Check (only fixes out of range states)
		key_indexes = obj.data.shape_key_labels[index].indexes
		for x in reversed(range(len(key_indexes))):
			if key_indexes[x].index >= len(keys.key_blocks):
				key_indexes.remove(x)
		
		# Find indexes in label
		indexes = [i.index for i in key_indexes if i.index > -1]
	else:
		if keys:
			indexes = [i for i in range(len(keys.key_blocks))]
		else:
			indexes = []
	
	selected = []
	if indexes:
		selected = get_visible_selection(obj, indexes)
		if not skip_view_mode_filter:			
			# Filter "ALL" label by view mode
			if context.scene.shape_keys_view_mode == 'SELECTED':
				indexes = selected[:]
			
			if context.scene.shape_keys_view_mode == 'VISIBLE':
				indexes = [i for i in indexes if not keys.key_blocks[i].mute]
				selected = [i for i in selected if i in indexes]
			if context.scene.shape_keys_view_mode == 'HIDDEN':
				indexes = [i for i in indexes if keys.key_blocks[i].mute]
				selected = [i for i in selected if i in indexes]
			
			if context.scene.shape_keys_view_mode == 'UNLABELED':
				indexes_set = set(indexes)
				for label in labels:
					for label_indexes in label.indexes:
						if label_indexes.index in indexes_set:
							indexes_set.remove(label_indexes.index)
				indexes = [i for i in indexes if i in indexes_set]
				selected = [i for i in selected if i in indexes]
	
	return indexes, selected


def remove_shape_index_from_label( index, label ):
	for x, i in enumerate(label.indexes):
		if index == i.index:
			label.indexes.remove(x)
			format_label_name( label )
			break


'''----------------------------------------------------------------------------
                            Shape Key Operators
----------------------------------------------------------------------------'''

def inline_vector_mult(vectorA, vectorB):
	'''Multiply each index of two vectors by each other, 
	so [vectorA[0] * vectorB[0], ...] '''
	return Vector([i * j for i, j in zip(vectorA, vectorB)])

def shape_keys_mute_others(shape_keys, selected_indexes):
	# Hide other shape keys and return their original states
	muted_states = []
	for x in range(len(shape_keys)):
		muted_states.append(shape_keys[x].mute)
		if x in selected_indexes:
			shape_keys[x].mute = False
		else:
			shape_keys[x].mute = True
	return muted_states

def shape_keys_restore_muted(shape_keys, muted_states):
	# Restore muted state
	for x in range(len(shape_keys)):
		shape_keys[x].mute = muted_states[x]

class ShapeKeyCreateCorrective(bpy.types.Operator):
	bl_idname = "object.shape_key_create_corrective"
	bl_label = "Create Corrective Driver"
	bl_description = "Create Corrective Driver from Selection"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		obj = context.object
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def execute(self, context):
		# Gather data
		
		obj = context.active_object
		mesh = obj.data
		active = obj.active_shape_key_index
		sel = Advanced_Shape_Key_Labels( context ).get_visible_item_indexes()[1]
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
			
		return{'FINISHED'} 

class ShapeKeyAxis(bpy.types.Operator):
	bl_idname = "object.shape_key_axis"
	bl_label = "Limit Axis"
	bl_description = "Adjust Shape Key Movement by Axis"
	bl_options = {'REGISTER', 'UNDO'}
	
	deform_axis = bpy.props.FloatVectorProperty(
		name = "Deform Axis", 
		description = "",
		default = (1, 1, 1),
		soft_min = 0,
		soft_max = 1,
		subtype = 'XYZ')
		
	selected = None
	invoked = False
	offsets = []

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def execute(self, context):
		obj = context.active_object
		label_accessor = Advanced_Shape_Key_Labels( context )
		shape_keys = label_accessor.get_items()
		
		# Initialize.  Isn't there a function for this?  Maybe that's only for modal operators.
		if self.invoked:
			# Gather data
			indexes, self.selected = label_accessor.get_visible_item_indexes()
			
			# Get offsets
			self.offsets = []			
			for x, i in enumerate(self.selected):
				offset_key = []
				for x in range(len(shape_keys[0].data)):
					offset = shape_keys[i].data[x].co - shape_keys[0].data[x].co
					if offset != 0.0:
						offset_key.append(( x, offset ))
				self.offsets.append(offset_key)
		
		# Apply offsets
		for x, i in enumerate(self.selected):
			for x, offset in self.offsets[x]:
				shape_keys[i].data[x].co = shape_keys[0].data[x].co + inline_vector_mult(offset, self.deform_axis)
	
		obj.data.update()
		
		self.invoked = False
		return{'FINISHED'} 
	
	def invoke(self, context, event):
		self.invoked = True
		return self.execute(context)
		
class ToggleShapeKey(bpy.types.Operator):
	bl_idname = "object.shape_key_toggle"
	bl_label = "Inverse Visibility of Selected"
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = "Inverse Visibility of Selected"
	
	shift = bpy.props.BoolProperty(default = True, description = "Rotate Visible in Selection")
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		obj = context.active_object
		label_accessor = Advanced_Shape_Key_Labels( context )
		indexes, selected = label_accessor.get_visible_item_indexes( )
		shape_keys = label_accessor.get_items()

		if selected:
			if not self.shift or len(selected) == 1:
				# Inverse Selected Visible
				for i in selected:
					shape_keys[i].mute = not shape_keys[i].mute
			else:
				# Rotate Selected Visible
				vis = [x for x, i in enumerate(selected) if not shape_keys[i].mute]
				if len(vis) != 1:
					for i in selected:
						shape_keys[i].mute = 1
					shape_keys[selected[0]].mute = 0
					vis = [0]
				
				vis = vis[0]
				shape_keys[selected[vis]].mute = True
				shape_keys[selected[vis - 1]].mute = False		
		return{'FINISHED'} 

class NegateShapeKey(bpy.types.Operator):
	bl_idname = "object.shape_key_negate"
	bl_label = "Negate Weight of Selected"
	bl_description = "Negate Weight of Selected"
	bl_options = {'REGISTER', 'UNDO'}
	
	selected = bpy.props.BoolProperty(default = True, description = "Negate Weight of Visible")
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def invoke(self, context, event):
		# self.initial_global_undo_state = bpy.context.user_preferences.edit.use_global_undo
		self.selected = not event.shift
		return self.execute(context)
	
	def execute(self, context):
		# Data Gathering
		obj = context.active_object
		label_accessor = Advanced_Shape_Key_Labels( context )
		indexes, selected = label_accessor.get_visible_item_indexes( )
		shape_keys = label_accessor.get_items()
		
		# Operate on selected
		if self.selected:
			indexes = selected
		
		# Inverse Weights
		for i in indexes:
			if shape_keys[i].value >= 0:
				shape_keys[i].slider_min = -1.0
				shape_keys[i].value = -1.0
			else:
				shape_keys[i].slider_min = 0.0
				shape_keys[i].value = 1
		return{'FINISHED'} 

class ShapeKeyCopy(bpy.types.Operator):
	bl_idname = "object.shape_key_copy"
	bl_label = "Create New Shape Key from Selected"
	bl_description = "Create New Shape Key from Selected"
	bl_options = {'REGISTER', 'UNDO'}
	
	mirror = bpy.props.BoolProperty(default = False, description = "Create Mirror from Selected Shape Keys")
	selected = bpy.props.BoolProperty(default = True, description = "Create New Shape Key from Visible")
	absolute = bpy.props.BoolProperty(default = False, description = "Copy Shape Key at a value of 1.")
	initial_global_undo_state = None
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
	
	def invoke(self, context, event):
		# self.initial_global_undo_state = bpy.context.user_preferences.edit.use_global_undo
		self.selected = not event.shift
		self.absolute = event.ctrl
		return self.execute(context)
		
			
	def execute(self, context):
		# Data gathering
		obj = context.object
		active_index = obj.active_shape_key_index
		label_accessor = Advanced_Shape_Key_Labels( context )
		indexes, selected = label_accessor.get_visible_item_indexes( )
		shape_keys = label_accessor.get_items()
		
		if not self.selected:
			# Do add_to_label, with from mix = True
			bpy.ops.object.shape_key_add_to_label(from_mix = not self.absolute)
			new_shape = shape_keys[obj.active_shape_key_index]
			
		else:
			# Hide other shape keys and save their states
			muted_states = shape_keys_mute_others(shape_keys, selected)
			muted_states.append(False)
			
			# Copy
			bpy.ops.object.shape_key_add_to_label(from_mix = not self.absolute)
			new_shape = shape_keys[obj.active_shape_key_index]
			
			# Restore states
			shape_keys_restore_muted(shape_keys, muted_states)
		
		if self.absolute:
			# Copy Absolute (copy the shape as if it were at a value of 1)
			if self.selected:
				copy_indexes = selected
			else:
				copy_indexes = [i for i in indexes if not shape_keys[i].mute]
			new_index = obj.active_shape_key_index
			
			for i in copy_indexes:
				for y in range(len(shape_keys[active_index].data)):
					shape_keys[new_index].data[y].co += shape_keys[i].data[y].co - shape_keys[0].data[y].co
		if self.mirror:
			bpy.ops.object.shape_key_mirror()
		
		if len(indexes) == 1 or (len(selected) == 1 and self.selected):
			# Copy state from original
			new_shape.value = 1.0 #shape_keys[active_index].value
			# new_shape.slider_max = shape_keys[active_index].slider_max
			# new_shape.slider_min = shape_keys[active_index].slider_min
			name = shape_keys[active_index].name
			
		else:
			# Turn on
			new_shape.value = 1.0
			new_shape.mute = False
			name = 'New Key'
		
		if self.mirror:
			new_shape.name = name + " Mirrored"
		elif not self.selected:
			new_shape.name = name + " Copy"
		
		# if self.initial_global_undo_state:
			# bpy.context.user_preferences.edit.use_global_undo = self.initial_global_undo_state
		return{'FINISHED'}

class ShapeKeyScrubTwo(bpy.types.Operator):
	bl_idname = "object.shape_key_scrub_two"
	bl_label = "Scrub Between Two Shape Keys"
	bl_description = "Scrub Between Two Shape Keys"
	bl_options = {'REGISTER', 'UNDO'}
	
	percent = bpy.props.FloatProperty(
		name = "Percent",
		default = 0.5,
		soft_min = 0,
		soft_max = 1,
		subtype = 'FACTOR'
		)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def execute(self, context):		
		# Get indexes of visible keys
		label_accessor = Advanced_Shape_Key_Labels( context )
		indexes, selected = label_accessor.get_visible_item_indexes( )
		
		if len(selected) == 2:
			shape_keys = label_accessor.get_items()
			shape_keys[sel[0]].value = self.percent
			shape_keys[sel[1]].value = 1.0 - self.percent
		return {'FINISHED'}

'''----------------------------------------------------------------------------
                            Label Operators
----------------------------------------------------------------------------'''

class ShapeKeyLabelAdd(bpy.types.Operator):
	bl_idname = "object.shape_key_label_add"
	bl_label = "Add Label"
	bl_description = "Add Label"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_mode = False)
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).add( )
		return {'FINISHED'} 

class ShapeKeyLabelRemove(bpy.types.Operator):
	bl_idname = "object.shape_key_label_remove"
	bl_label = "Remove Label"
	bl_description = "Remove Label"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_mode = False)
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).remove( )
		return {'FINISHED'} 

class ShapeKeyLabelMove(bpy.types.Operator):
	bl_idname = "object.shape_key_label_move"
	bl_label = "Move Label"
	bl_description = "Move Label"
	bl_options = {'REGISTER', 'UNDO'}
	
	type = bpy.props.EnumProperty(
		name="Move Label Direction",
		items =	(('UP', "Up", "Up"),
				('DOWN', "Down", "Down"),
				),
		default = 'UP'
		)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_mode = False)
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).move( direction = self.type )
		return {'FINISHED'} 

class ShapeKeySetIndex(bpy.types.Operator):
	bl_idname = "object.shape_key_set_index"
	bl_label = "Set Active Shape Key"
	bl_description = "Set Active Shape Key"
	bl_options = {'REGISTER', 'UNDO'}
	
	index = bpy.props.IntProperty(default = -1)
	shift = bpy.props.BoolProperty(default = False)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def draw(self, context):
		pass
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).select_item( self.index, self.shift )
		return {'FINISHED'}
	
class ShapeKeyCopyToLabel(bpy.types.Operator):
	bl_idname = "object.shape_key_copy_to_label"
	bl_label = "Copy To Label"
	bl_description = "Copy To Label"
	bl_options = {'REGISTER', 'UNDO'}
	
	index = bpy.props.IntProperty(default = -1)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
	
	def draw(self, context):
		pass
	
	def execute(self, context):
		copied_to = Advanced_Shape_Key_Labels( context ).copy_item( self.index )
		if copied_to is not None:
			self.report({'INFO'}, "Copied to %s" % copied_to)
		return {'FINISHED'}

class ShapeKeyAddToLabel(bpy.types.Operator):
	bl_idname = "object.shape_key_add_to_label"
	bl_label = "Add to Label"
	bl_description = "Add to Label"
	bl_options = {'REGISTER', 'UNDO'}
	
	from_mix = bpy.props.BoolProperty(
		name = "Add To Label From Mix",
		default = False)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context)
	
	def draw(self, context):
		pass
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).add_item( )
		return {'FINISHED'}

class ShapeKeyRemoveFromLabel(bpy.types.Operator):
	bl_idname = "object.shape_key_remove_from_label"
	bl_label = "Remove From Label"
	bl_description = "Remove From Label"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		obj = context.object
		if not label_poll(context):
			return False
		
		labels = obj.data.shape_key_labels
		index = obj.active_shape_key_label_index
		return (labels and index > 0)
	
	def draw(self, context):
		pass
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).remove_item( )
		return {'FINISHED'}

class ShapeKeyDelete(bpy.types.Operator):
	bl_idname = "object.shape_key_delete"
	bl_label = "Delete Shape Key"
	bl_description = "Delete Shape Key"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
		
	def draw(self, context):
		pass

	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).delete_item( )
		return {'FINISHED'}

class ShapeKeyMoveInLabel(bpy.types.Operator):
	bl_idname = "object.shape_key_move_in_label"
	bl_label = "Move Shape Key"
	bl_description = "Move Shape Key"
	bl_options = {'REGISTER', 'UNDO'}
	
	type = bpy.props.EnumProperty(
		name="Move Shape Key Direction",
		items =	(('UP', "Up", "Up"),
				('DOWN', "Down", "Down"),
				),
		default = 'UP'
		)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).move_item( direction = self.type )
		return {'FINISHED'}

class ShapeKeyToggleSelected(bpy.types.Operator):
	bl_idname = "object.shape_key_toggle_selected"
	bl_label = "Toggle Selected Shape Keys"
	bl_description = "Toggle Selected Shape Keys"
	bl_options = {'REGISTER', 'UNDO'}
	
	shift = bpy.props.BoolProperty(default = False)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def draw(self, context):
		pass
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).toggle_selected_item( inverse = not self.shift )
		return {'FINISHED'}
		
class ShapeKeyToggleVisible(bpy.types.Operator):
	bl_idname = "object.shape_key_toggle_visible"
	bl_label = "Toggle Visible Shape Keys"
	bl_description = "Toggle Visible Shape Keys"
	bl_options = {'REGISTER', 'UNDO'}
	
	
	shift = bpy.props.BoolProperty(default = False)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)
	
	def draw(self, context):
		pass
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		Advanced_Shape_Key_Labels( context ).toggle_visible_item( inverse = not self.shift )
		return {'FINISHED'}

class MESH_MT_shape_key_view_mode(Menu):
	bl_label = "View Mode"

	def draw(self, context):
		layout = self.layout
		obj = context.object
		for item in bpy.types.Scene.shape_keys_view_mode[1]['items']:
			if item[0] == 'UNLABELED' and obj.data.shape_key_labels and obj.active_shape_key_label_index != 0:
				continue
				
			if item[0] != context.scene.shape_keys_view_mode:
				layout.prop_enum(context.scene, "shape_keys_view_mode", item[0])

class MESH_MT_shape_key_copy_to_label(Menu):
	bl_label = "Copy Shape Key to Label"

	def draw(self, context):
		layout = self.layout
		obj = context.object
		for x, label in enumerate(obj.data.shape_key_labels):
			if x > 0:
				layout.operator("object.shape_key_copy_to_label", icon='FILE_FOLDER', text = label.name).index = x

class NullOperator(bpy.types.Operator):
	bl_idname = "object.null_operator"
	bl_label = ""
	bl_icon = 'BLANK1'
	bl_options = {'REGISTER'}
	
	@classmethod
	def poll(cls, context):
		return True
	def execute(self, context):
		return {'FINISHED'} 

'''----------------------------------------------------------------------------
                            Shape Key Panel
----------------------------------------------------------------------------'''

class DATA_PT_shape_keys(MeshButtonsPanel, Panel):
	bl_label = "Shape Keys"

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_mode = False)
		
	def draw(self, context):
		layout = self.layout

		ob = context.object
		label_accessor = Advanced_Shape_Key_Labels( context )
		indexes, selected = label_accessor.get_visible_item_indexes( )
		shape_keys = label_accessor.get_items()
		key = ob.data.shape_keys
		kb = ob.active_shape_key
	
		##########################
		# LABELS LIST
		layout.label("Labels")
		row = layout.row()
		row.template_list(ob.data, "shape_key_labels", ob, "active_shape_key_label_index", rows = 4) #
	
		col = row.column() #.split(percentage = 0.5)
		sub = col.column( align=True )
		sub.operator("object.shape_key_label_add", icon = 'ZOOMIN', text="")
		sub.operator("object.shape_key_label_remove", icon = 'ZOOMOUT', text="")
		
		
		sub =  col.column()
		sub.separator()
		sub.scale_y = 4.9
		
		sub =  col.column(align=True)
		sub.operator("object.shape_key_label_move", icon = 'TRIA_UP', text = "").type = 'UP'
		sub.operator("object.shape_key_label_move", icon = 'TRIA_DOWN', text = "").type = 'DOWN'
		
	
		labels = ob.data.shape_key_labels
		if labels:
			row = layout.row()
			row.prop(labels[ob.active_shape_key_label_index], 'name')

		
		##########################
		# SIDE COLUMN ICONS
		row = layout.row()
		box = row.box()
		col = row.column()
		col.separator()
		side_col = col.column(align=True)
		side_col.operator("object.shape_key_add_to_label", icon = 'ZOOMIN', text = "").from_mix = False
		side_col.operator("object.shape_key_remove_from_label", icon = 'ZOOMOUT', text = "")
		side_col.operator("object.shape_key_delete", icon = 'PANEL_CLOSE', text = "")
		
		indexes, selected = get_visible_indexes( context)
		
		if indexes:
			side_col.operator("object.shape_key_toggle", icon = 'RESTRICT_VIEW_OFF', text = '')
			side_col.operator("object.shape_key_copy", icon = 'PASTEDOWN', text = '')
			side_col.operator("object.shape_key_copy", icon = 'ARROW_LEFTRIGHT', text = '').mirror = True
			side_col.operator("object.shape_key_negate", icon = 'FORCE_CHARGE', text = '')
			side_col.operator("object.shape_key_axis", icon = 'MANIPUL', text = '')
			side_col.operator("object.shape_key_scrub_two", icon = 'IPO', text = '')
			
		side_col.menu("MESH_MT_shape_key_specials", icon = 'DOWNARROW_HLT', text = "")
		#shape_key_add_to_label
		if shape_keys:
			row = box.row()
			
			##########################
			# SHAPE KEY VIEW MODE / COPY TO
			# if ob.data.shape_key_labels and ob.active_shape_key_label_index == 0:
			# Display view mode menu if "ALL" label is selected
			menu_name = next(item[1] for item in bpy.types.Scene.shape_keys_view_mode[1]['items'] if context.scene.shape_keys_view_mode == item[0])
			row.menu("MESH_MT_shape_key_view_mode", text = menu_name)
			row = row.split()
			
			row.label("Shape Keys")
			
			if ob.data.shape_key_labels and len(ob.data.shape_key_labels) > 1:	
				row = row.split()
				row.menu("MESH_MT_shape_key_copy_to_label", text = "Copy to Label")
		
		if indexes:
			##########################
			# SHAPE KEYS
			for i in indexes:
				row = box.row(align = True)
				row.scale_y = 0.8
				row = row.split(percentage = 0.09)
				icon = 'PROP_OFF'
				if i == ob.active_shape_key_index:
					icon = 'PROP_ON'
				elif i in selected:
					icon = 'PROP_CON'
				row.operator("object.shape_key_set_index", icon = icon, text = '').index = i
				
				row.prop(shape_keys[i], 'name', text = '')
				row = row.split(percentage = 0.85)
				row.prop(shape_keys[i], 'value', text = '')
				row = row.split()
				row.prop(shape_keys[i], 'mute', text = '')
			
			##########################
			# SHAPE KEYS BOTTOM ROW TOGGLES

			row = box.row(align = True)
			row.scale_y = 0.8
			row = row.split(percentage = 0.10, align = True)
			row.operator("object.shape_key_toggle_selected", icon = 'PROP_ON', text = '')
			
			row = row.split(percentage = 0.91, align = True)
			row.label('')
			
			row.operator("object.shape_key_toggle_visible", icon = 'VISIBLE_IPO_ON', text = '') #.absolute = True
			
			##########################
			# SIDE COLUMN BOTTOM ICONS
			
			# A trip to photoshop gave me this.
			# However, this may break cross platform due to differences in icon size
			# A better solution would be a way to attach columns to the bottom of another element
			# But I don't believe this is possible with the current API
			
			side_icons = 6 + 6
			button_space = len(indexes) * 24 - 4 + 30 # + 9 #shapekey row adds 30ish, Extra bottom row as padding adds 9ish.
			side_space = side_icons * 20 + 4	# This may be incorrect if side_icons is less than 4
			space = button_space - side_space
			if space > 0:
				side_col = side_col.column()
				side_col.scale_y = space / 6.0
				side_col.separator()			
			side_col =  col.column(align=True)
			side_col.operator("object.shape_key_move_in_label", icon = 'TRIA_UP', text = "").type = 'UP'
			side_col.operator("object.shape_key_move_in_label", icon = 'TRIA_DOWN', text = "").type = 'DOWN'
			
			
			##########################
			# THE REST OF THE DEFAULT INTERFACE
			# (Minus the name field, which I removed)
			
			enable_edit = ob.mode != 'EDIT'
			enable_edit_value = False

			if ob.show_only_shape_key is False:
				if enable_edit or (ob.type == 'MESH' and ob.use_shape_key_edit_mode):
					enable_edit_value = True
			
			split = layout.split() #percentage = 0.3)
			row = split.row()
			row.enabled = enable_edit
			row.prop(key, "use_relative")
			
			row = split.row()
			row.alignment = 'RIGHT'
			
			sub = row.row(align=True)
			sub.label()  # XXX, for alignment only
			subsub = sub.row(align=True)
			subsub.active = enable_edit_value
			subsub.prop(ob, "show_only_shape_key", text = "")
			sub.prop(ob, "use_shape_key_edit_mode", text = "")

			
			sub = row.row()
			if key.use_relative:
				sub.operator("object.shape_key_clear", icon = 'X', text="")
			else:
				sub.operator("object.shape_key_retime", icon = 'RECOVER_LAST', text = "")

			if key.use_relative:
				if ob.active_shape_key_index != 0:
					row = layout.row()
					row.active = enable_edit_value
					row.prop(kb, 'value')

					split = layout.split()

					col = split.column(align = True)
					col.active = enable_edit_value
					col.label(text = "Range:")
					col.prop(kb, 'slider_min', text = "Min")
					col.prop(kb, 'slider_max', text = "Max")

					col = split.column(align = True)
					col.active = enable_edit_value
					col.label(text = "Blend:")
					col.prop_search(kb, 'vertex_group', ob, 'vertex_groups', text='')
					col.prop_search(kb, 'relative_key', key, 'key_blocks', text='')

			else:
				row = layout.column()
				row.active = enable_edit_value
				row.prop(key, 'eval_time')
				row.prop(key, 'slurph')
		row = box.row(align = True)
		
def label_index_updated(self, context):
	Advanced_Shape_Key_Labels( context ).label_index_updated()
	
def shape_key_specials(self, context):
	self.layout.operator("object.shape_key_create_corrective", 
		text = "Create Corrective Driver", 
		icon = 'LINK_AREA')

old_shape_key_menu = None
def register():
	# Register collections
	try:
		bpy.utils.register_class(IndexProperty)
		bpy.utils.register_class(IndexCollection)
	except:
		pass

	# Add rna for Mesh object, to store label names and corresponding indexes.
	bpy.types.Mesh.shape_key_labels = bpy.props.CollectionProperty(type = IndexCollection)
	bpy.types.Object.selected_shape_keys = bpy.props.CollectionProperty(type = IndexProperty)
	bpy.types.Object.active_shape_key_label_index = bpy.props.IntProperty( default = 0, update = label_index_updated)
	
	# Replace shapekeys panel with my own
	global old_shape_key_menu
	old_shape_key_menu = bpy.types.DATA_PT_shape_keys
	
	# I wish I knew how to extend existing operators like object.shape_key_move
	# So I could override those with mine, and not risk my label state machine
	# becoming invalid if some other script/user calls object.shape_key_move
	# instead of object.shape_key_move_to_label
	
	bpy.types.Scene.shape_keys_view_mode = bpy.props.EnumProperty(
		name="View",
		items =	(('ALL', "All", "View All Shape Keys"),
				('UNLABELED', "Unlabeled", "View Unlabeled Shape Keys"),
				('SELECTED', "Selected", "View Selected Shape Keys"),
				('VISIBLE', "Visible", "View Visible Shape Keys"),
				('HIDDEN', "Hidden", "View Hidden Shape Keys"),
				),
		)
	
	bpy.types.MESH_MT_shape_key_specials.append(shape_key_specials)

	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_class(IndexProperty)
	bpy.utils.unregister_class(IndexCollection)
	bpy.utils.unregister_module(__name__)
	bpy.utils.register_class(old_shape_key_menu)
	bpy.types.MESH_MT_shape_key_specials.remove(shape_key_specials)
	
	del bpy.types.Scene.shape_keys_view_mode
	
	# Should I delete the rna types created?  Hmmmm.  
	# I don't want a user to lose data from reloading my addon,
	# but I also don't want extra data saved if it's permanently disabled.
	# I think the lesser evil here is not to delete data.
	
if __name__ == "__main__":
	register()
