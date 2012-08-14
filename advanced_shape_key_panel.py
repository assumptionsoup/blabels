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

bl_info = {
    "name": "Advanced Shapekey Panel",
    "author": "Jordan Hueckstaedt",
    "version": (1, 0),
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

class MeshButtonsPanel():
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'

	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		return context.mesh and (engine in cls.COMPAT_ENGINES)


'''----------------------------------------------------------------------------
                            Label Helpers
----------------------------------------------------------------------------'''

def label_poll(context, test_shapes = False):
	# Simple function for most the poll methods in this module
	obj = context.object
	if not (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and \
		(context.scene.render.engine in {'BLENDER_RENDER', 'BLENDER_GAME'})):
		return False
	
	if test_shapes:
		return obj.data.shape_keys
	
	return True
	
def strip_label_number(label):
	# Remove numbers from label name and return it
	name = label.name
	name = name.split("(")[0]
	return name.strip("")
	
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

def get_visible_indexes(obj, context, skip_view_mode_filter = False):
	# Get visible shape key indexes
	labels = obj.data.shape_key_labels
	index = obj.active_shape_key_label_index
	keys = obj.data.shape_keys
	indexes = []
	if index != 0 and labels and len(labels):
		indexes = [i.index for i in obj.data.shape_key_labels[index].indexes if i.index > -1]
	else:
		if keys:
			indexes = [i for i in range(len(keys.key_blocks))]
		else:
			indexes = []
	
	selected = []
	if indexes and obj.data.shape_key_labels:	
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
		return label_poll(context, test_shapes = True)
	
	def execute(self, context):
		# Gather data
		obj = context.active_object
		mesh = obj.data
		active = obj.active_shape_key_index
		sel = get_visible_indexes(obj, context)[1]
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
	
	deform_axis = bpy.types.Scene.shape_key_axis_deform = bpy.props.FloatVectorProperty(
		name = "Deform Axis", 
		description = "",
		default = (1, 1, 1),
		soft_min = 0,
		soft_max = 1,
		subtype = 'XYZ')
		
	selected = None
	offsets = []

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
	
	def execute(self, context):
		obj = context.active_object
		shape_keys = obj.data.shape_keys.key_blocks
		
		# Initialize.  Isn't there a function for this?  Maybe that's only for modal operators.
		if self.selected is None:
			# Gather data
			indexes, self.selected = get_visible_indexes(obj, context)
			
			self.active_index = obj.active_shape_key_index
			
			# Get offsets		
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

		return{'FINISHED'} 
	
	def invoke(self, context, event):
		self.deform_axis = context.scene.shape_key_axis_deform
		return self.execute(context)


class ToggleShapeKey(bpy.types.Operator):
	bl_idname = "object.shape_key_toggle"
	bl_label = "Inverse Visibility of Selected"
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = "Inverse Visibility of Selected"
	
	shift = bpy.props.BoolProperty(default = True, description = "Rotate Visible in Selection")
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		obj = context.active_object
		indexes, selected = get_visible_indexes(obj, context)
		shape_keys = obj.data.shape_keys.key_blocks

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
		return label_poll(context, test_shapes = True)
	
	def invoke(self, context, event):
		# self.initial_global_undo_state = bpy.context.user_preferences.edit.use_global_undo
		self.selected = not event.shift
		return self.execute(context)
	
	def execute(self, context):
		# Data Gathering
		obj = context.active_object
		indexes, selected = get_visible_indexes(obj, context)
		shape_keys = obj.data.shape_keys.key_blocks
		
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
	initial_global_undo_state = None
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
	
	def invoke(self, context, event):
		# self.initial_global_undo_state = bpy.context.user_preferences.edit.use_global_undo
		self.selected = not event.shift
		return self.execute(context)
	
	def execute(self, context):
		# Data gathering
		obj = context.object
		shape_keys = obj.data.shape_keys.key_blocks
		active_index = obj.active_shape_key_index
		indexes, selected = get_visible_indexes(obj, context)
		
		if not self.selected:
			# Do add_to_label, with from mix = True
			bpy.ops.object.shape_key_add_to_label(from_mix = True)
			new_shape = shape_keys[obj.active_shape_key_index]
		
		else:
			# Hide other shape keys and save their states
			muted_states = shape_keys_mute_others(shape_keys, selected)
			muted_states.append(False)
			
			# Copy
			bpy.ops.object.shape_key_add_to_label(from_mix = True)
			new_shape = shape_keys[obj.active_shape_key_index]
			
			# Restore states
			shape_keys_restore_muted(shape_keys, muted_states)
		
		if self.mirror:
			bpy.ops.object.shape_key_mirror()
		
		if len(indexes) == 1 or (len(selected) == 1 and self.selected):
			# Copy state from original
			new_shape.value = shape_keys[active_index].value
			new_shape.slider_max = shape_keys[active_index].slider_max
			new_shape.slider_min = shape_keys[active_index].slider_min
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
		return label_poll(context)
	
	def execute(self, context):
		obj = context.object
		mesh = obj.data
		keys = mesh.shape_key_labels.keys()
		label = mesh.shape_key_labels.add()
		
		if not keys:
			label.name = "All"
			if obj.data.shape_keys:
				num_keys = len(obj.data.shape_keys.key_blocks)
			else:
				num_keys = 0
			format_label_name( label, num_keys)
		else:
			label.name = "Label %d" % len(keys)
			format_label_name( label )
		
		index = len( mesh.shape_key_labels.keys() ) - 1
		obj.active_shape_key_label_index = index

		return {'FINISHED'} 

class ShapeKeyLabelRemove(bpy.types.Operator):
	bl_idname = "object.shape_key_label_remove"
	bl_label = "Remove Label"
	bl_description = "Remove Label"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		return label_poll(context)
	
	def execute(self, context):
		obj = context.object
		mesh = obj.data
		keys = mesh.shape_key_labels.keys()
		index = obj.active_shape_key_label_index
		
		if keys and (index != 0 or len(keys) == 1):
			mesh.shape_key_labels.remove(index)
			obj.active_shape_key_label_index = min(len(keys) - 2, index)
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
		return label_poll(context)
	
	def execute(self, context):
		# Gather data
		obj = context.object
		mesh = obj.data
		keys = mesh.shape_key_labels.keys()
		index = obj.active_shape_key_label_index
		labels = mesh.shape_key_labels
		
		# Check for labels.  Don't move special label "ALL".
		if keys and index > 0:
			if self.type == 'UP':
				if index - 1 > 0:
					labels.move(index, index - 1)
					obj.active_shape_key_label_index -= 1
			else:
				if index + 1 < len(keys):
					labels.move(index, index + 1)
					obj.active_shape_key_label_index += 1
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
		return label_poll(context, test_shapes = True)
	
	def draw(self, context):
		pass
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		if self.index > -1:
			obj = context.object
			sel = obj.selected_shape_keys
			if not self.shift:
				# Clear selected if shift isn't used
				for x in range(len(sel)):
					sel.remove(0)
			else:
				for x, key in enumerate(sel):
					if self.index == key.index:
						if obj.active_shape_key_index == self.index:
							if len(sel) > 1:
								sel.remove(x)
								obj.active_shape_key_index = sel[-1].index
						else:
							sel.remove(x)
						return {'FINISHED'}
			# Set active
			obj.active_shape_key_index = self.index
			
			# Add to selected
			i = obj.selected_shape_keys.add()
			i.index = self.index

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
		obj = context.object
		mesh = obj.data
		label = mesh.shape_key_labels[self.index]
		
		# Get indexes
		label_indexes = [i.index for i in label.indexes]
		selected = get_visible_indexes( obj, context )[1]

		# Only add indexes that aren't already in that label
		add_indexes = []
		for i in selected:
			if i not in label_indexes:
				add_indexes.append(i)
		
		# Add 'em
		for i in add_indexes:
			indexes = label.indexes.add()
			indexes.index = i
		
		if add_indexes:
			self.report({'INFO'}, "Copied to %s" % strip_label_number(label))
			format_label_name(label)
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
		obj = context.object
		mesh = obj.data
		index = obj.active_shape_key_label_index
		labels =  mesh.shape_key_labels
		bpy.ops.object.shape_key_add(from_mix = self.from_mix)
		
		# Add to current label if on is selected.
		if index > 0:
			label = labels[index]
			label_index = label.indexes.add()
			label_index.index = obj.active_shape_key_index
			format_label_name(label)
		
		# Update "All" Label
		if labels:
			num_keys = 0
			if mesh.shape_keys:
				num_keys = len(mesh.shape_keys.key_blocks)
			format_label_name(labels[0], num_keys)
		
		# Update selected
		for x in range(len(obj.selected_shape_keys)):
			obj.selected_shape_keys.remove(0)
		selected_index = obj.selected_shape_keys.add()
		selected_index.index = obj.active_shape_key_index
		
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
		obj = context.object
		mesh = obj.data
		index = obj.active_shape_key_label_index
		if index > 0:
			label = mesh.shape_key_labels[index]			
			
			# get selected
			sel = get_visible_indexes( obj, context )[1]
			sel.sort()
			sel.reverse()
			for i in sel:
				remove_shape_index_from_label( i, label )
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

	def delete_active_shape_key(self, obj):
		mesh = obj.data
		shape_index = obj.active_shape_key_index
		bpy.ops.object.shape_key_remove()
		
		if mesh.shape_key_labels:
			# Update "All" Label
			if obj.data.shape_keys:
				num_keys = len(obj.data.shape_keys.key_blocks)
			else:
				num_keys = 0
			format_label_name( mesh.shape_key_labels[0], num_keys)
			
			# Update other labels
			if len(obj.data.shape_key_labels) > 1:
				for x in range(1, len(mesh.shape_key_labels)):
					remove_shape_index_from_label(shape_index, mesh.shape_key_labels[x])
				
				# Correct the moved index in every label (except the first label, All)
				for x in range(1, len(obj.data.shape_key_labels)):
					label_indexes = obj.data.shape_key_labels[x].indexes
					for label_index in label_indexes:
						if label_index.index >= shape_index:
							label_index.index -= 1
			
	def execute(self, context):
		obj = context.object
		mesh = obj.data
		
		# Delete selected
		sel = get_visible_indexes( obj, context )[1]
		if sel:
			sel.sort()
			sel.reverse()
			for i in sel:
				obj.active_shape_key_index = i
				self.delete_active_shape_key(obj)
			
			# Update active index
			if mesh.shape_keys and len(mesh.shape_keys.key_blocks) > obj.active_shape_key_index + 1:
				obj.active_shape_key_index += 1
			
			# Update selected
			for sel in obj.selected_shape_keys:
				obj.selected_shape_keys.remove(0)
			s = obj.selected_shape_keys.add()
			s.index = obj.active_shape_key_index
		
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
		return label_poll(context, test_shapes = True)
	
	def execute(self, context):
		obj = context.object
		mesh = obj.data
		index = obj.active_shape_key_label_index
		
		# Get indexes of visible keys
		indexes, sel = get_visible_indexes(obj, context)
		
		# If it's a real label
		if index > 0:
			# I'm sure there's a better way to do this.
			
			# Do everything in reverse if going down
			if self.type == 'DOWN':
				indexes.reverse()
			
			# Indexes of selected keys
			pos = [indexes.index(i) for i in sel]
			pos.sort()
			
			# Indexes are in order, beginning at 0, and therefore at the start of the list
			# and can be skipped
			if pos == list(range(len(pos))):
				return {'FINISHED'}

			# Move selections that are at the beginning of the list out of the operation.
			new_indexes = []
			while pos and pos[0] == 0:
				new_indexes.append(indexes.pop(0))
				pos = [pos[y] - 1 for y in range(1, len(pos))]
			
			# The main logic I'm using.  I really wish this whole thing was better.
			delayed = []			
			for x, i in enumerate(indexes):
				if x + 1 in pos:
					new_indexes.append(indexes[x + 1])
					delayed.append(i)
				else:
					for y in reversed(range(len(delayed))):
						d = delayed.pop(y)
						if d not in new_indexes:
							new_indexes.append(d)
					if i not in new_indexes:
						new_indexes.append(i)
			
			# Restore direction
			if self.type == 'DOWN':
				new_indexes.reverse()
			
			# Apply changes
			for x, i in enumerate(new_indexes):
				obj.data.shape_key_labels[index].indexes[x].index = i			
		else:
			# Sort visible
			sel.sort()
			
			# Reverse it if going down to help with clashes
			if self.type == 'DOWN':
				sel.reverse()
			
			key_index = obj.active_shape_key_index
			new_key_index = -1
			increment = -1
			if self.type == 'DOWN':
				increment = 1
			
			for x, i in enumerate(sel):
				# Only move down if it won't run into another selected item
				if (i + increment) not in sel:
					# Set active index, move shape key
					obj.active_shape_key_index = i
					bpy.ops.object.shape_key_move(type = self.type)
					new_index = obj.active_shape_key_index
					
					# Update actual selection
					obj.selected_shape_keys[x].index = new_index
					
					# Update selected items, so item clashes resolve correctly
					sel[x] = new_index
					
					# Save active_index, so it can be restored correctly later
					if i == key_index:
						new_key_index = new_index
					
					# Correct the moved index in every label (except the first label, All)
					if obj.data.shape_key_labels and len(obj.data.shape_key_labels) > 1:
						for y in range(1, len(obj.data.shape_key_labels)):
							label_indexes = obj.data.shape_key_labels[y].indexes
							for label_index in label_indexes:
								if label_index.index == i:
									label_index.index = new_index
								elif label_index.index == new_index:
									label_index.index = i
			# Restore active_index			
			if new_key_index > -1:
				obj.active_shape_key_index = new_key_index
		return {'FINISHED'}

class ShapeKeyToggleSelected(bpy.types.Operator):
	bl_idname = "object.shape_key_toggle_selected"
	bl_label = "Toggle Selected Shape Keys"
	bl_description = "Toggle Selected Shape Keys"
	bl_options = {'REGISTER', 'UNDO'}
	
	shift = bpy.props.BoolProperty(default = False)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
	
	def draw(self, context):
		pass
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		obj = context.object
		
		actual_indexes, actual_selected = get_visible_indexes(obj, context, skip_view_mode_filter = True)
		
		# Clean selected
		for x in range(len(obj.selected_shape_keys)):
			obj.selected_shape_keys.remove(0)
		
		if not self.shift:
			# Select or de-select all
			if len(actual_selected) >= 0 and len(actual_selected) != len(actual_indexes):
				for i in actual_indexes:
					index = obj.selected_shape_keys.add()
					index.index = i
		else:
			# Inverse selection
			actual_selected = set(actual_selected)
			for i in actual_indexes:
				if i not in actual_selected:
					index = obj.selected_shape_keys.add()
					index.index = i
		
		# Correct active index.  Correct for 0 selected.
		selected = [i.index for i in obj.selected_shape_keys]
		if selected:
			if obj.active_shape_key_index not in selected:
				obj.active_shape_key_index = selected[-1]
		else:
			obj.active_shape_key_index = 0
			index = obj.selected_shape_keys.add()
			index.index = 0
		return {'FINISHED'}
		
class ShapeKeyToggleVisible(bpy.types.Operator):
	bl_idname = "object.shape_key_toggle_visible"
	bl_label = "Toggle Visible Shape Keys"
	bl_description = "Toggle Visible Shape Keys"
	bl_options = {'REGISTER', 'UNDO'}
	
	
	shift = bpy.props.BoolProperty(default = False)
	
	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)
	
	def draw(self, context):
		pass
	
	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)
	
	def execute(self, context):
		obj = context.object
		keys = obj.data.shape_keys.key_blocks
		
		indexes, selected = get_visible_indexes(obj, context)
		
		if not self.shift:
			# Hide or show all
			if any(1 for i in indexes if keys[i].mute):
				for i in indexes:
					keys[i].mute = False
			else:
				for i in indexes:
					keys[i].mute = True
		else:
			# Inverse Visible
			for i in indexes:
				keys[i].mute = not keys[i].mute
		
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
		return label_poll(context)
		
	def draw(self, context):
		layout = self.layout

		ob = context.object
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
		
		indexes, selected = get_visible_indexes(ob, context)
		
		if indexes:
			side_col.operator("object.shape_key_toggle", icon = 'RESTRICT_VIEW_OFF', text = '')
			side_col.operator("object.shape_key_copy", icon = 'PASTEDOWN', text = '')
			side_col.operator("object.shape_key_copy", icon = 'ARROW_LEFTRIGHT', text = '').mirror = True
			side_col.operator("object.shape_key_negate", icon = 'FORCE_CHARGE', text = '')
			side_col.operator("object.shape_key_axis", icon = 'MANIPUL', text = '')
		
		side_col.menu("MESH_MT_shape_key_specials", icon = 'DOWNARROW_HLT', text = "")
		#shape_key_add_to_label
		if key:
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
				
				row.prop(ob.data.shape_keys.key_blocks[i], 'name', text = '')
				row = row.split(percentage = 0.85)
				row.prop(ob.data.shape_keys.key_blocks[i], 'value', text = '')
				row = row.split()
				row.prop(ob.data.shape_keys.key_blocks[i], 'mute', text = '')
			
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
			
			side_icons = 6 + 5
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
	obj = context.object
	
	if obj.data.shape_key_labels and \
		context.scene.shape_keys_view_mode == 'UNLABELED' and \
		obj.active_shape_key_label_index != 0:
		
		context.scene.shape_keys_view_mode = 'ALL'
	
def shape_key_specials(self, context):
	self.layout.operator("object.shape_key_create_corrective", 
		text = "Create Corrective Driver", 
		icon = 'LINK_AREA')

# Define Shape Key Label collection to be put on mesh object.
class IndexProperty(bpy.types.PropertyGroup):
	index = bpy.props.IntProperty( default = -1)

class IndexCollection(bpy.types.PropertyGroup):
	indexes = bpy.props.CollectionProperty(type = IndexProperty)
	#name = bpy.props.StringProperty(name = "Label Name", default = "Default")
	
old_shape_key_menu = None
def register():
	# Register collections
	bpy.utils.register_class(IndexProperty)
	bpy.utils.register_class(IndexCollection)

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
