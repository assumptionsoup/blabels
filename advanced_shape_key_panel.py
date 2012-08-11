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

def get_visible_indexes(obj):
	# Get visible shape key indexes
	labels = obj.data.shape_key_labels
	index = obj.active_shape_key_label_index
	if index != 0 and labels and len(labels):
		return [i.index for i in obj.data.shape_key_labels[index].indexes if i.index > -1]
	else:
		if obj.data.shape_keys:
			return [i for i in range(len(obj.data.shape_keys.key_blocks))]
		else:
			return []
def get_visible_selected(obj):
	# Get visible selected shape key indexes
	indexes = get_visible_indexes(obj)
	
	# Use sets for intersection for speed - might not matter due to creation time
	indexes = set(indexes)
	
	# Get selected
	selected = [i.index for i in obj.selected_shape_keys]
	if not selected:
		selected = [obj.active_shape_key_index]
	
	return [i for i in selected if i in indexes]

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

def shape_key_copy():
	obj = bpy.context.active_object
	active_index = obj.active_shape_key_index
	shape_keys = obj.data.shape_keys.key_blocks
	name = shape_keys[active_index].name
	
	# Hide other shape keys and save their states
	muted_states = shape_keys_mute_others(shape_keys, get_visible_selected(obj))
	muted_states.append(False)
	
	# Copy
	bpy.ops.object.shape_key_add_to_label(from_mix = True)
	new_index = obj.active_shape_key_index
	shape_keys[new_index].value = shape_keys[active_index].value
	shape_keys[new_index].slider_max = shape_keys[active_index].slider_max
	shape_keys[new_index].slider_min = shape_keys[active_index].slider_min
	
	# Restore states
	shape_keys_restore_muted(shape_keys, muted_states)
	
	return shape_keys[new_index], name

class ShapeKeyCreateCorrective(bpy.types.Operator):
	bl_idname = "object.shape_key_create_corrective"
	bl_label = "Create Corrective Driver"
	bl_description = "Create Corrective Driver from Selection"
	bl_options = {'REGISTER', 'UNDO'}
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and 
			(engine in cls.COMPAT_ENGINES) and obj.data.shape_keys)
	
	def execute(self, context):
		# Gather data
		obj = bpy.context.active_object
		mesh = obj.data
		active = obj.active_shape_key_index
		sel = get_visible_selected(obj)
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
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	deform_axis = bpy.types.Scene.shape_key_axis_deform = bpy.props.FloatVectorProperty(
		name = "Deform Axis", 
		description = "",
		default = (1, 1, 1),
		soft_min = 0,
		soft_max = 1,
		subtype = 'XYZ')
		
	active_index = None
	offsets = []

	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and 
			(engine in cls.COMPAT_ENGINES) and obj.data.shape_keys)
	
	def execute(self, context):
		obj = bpy.context.active_object
		shape_keys = obj.data.shape_keys.key_blocks
		
		# Initialize.  Isn't there a function for this?  Maybe that's only for modal operators.
		if self.active_index is None:
			# Gather data
			self.active_index = obj.active_shape_key_index
			
			# Get basis
			for x in range(len(shape_keys[0].data)):
				offset = shape_keys[self.active_index].data[x].co - shape_keys[0].data[x].co
				if offset != 0.0:
					self.offsets.append( (x, offset) )
			
		for x, offset in self.offsets:
			shape_keys[self.active_index].data[x].co = shape_keys[0].data[x].co + inline_vector_mult(offset, self.deform_axis)
	
		obj.data.update()

		return{'FINISHED'} 
	
	def invoke(self, context, event):
		self.deform_axis = context.scene.shape_key_axis_deform
		return self.execute(context)


class ToggleShapeKey(bpy.types.Operator):
	bl_idname = "object.shape_key_toggle"
	bl_label = "Toggle Visible"
	bl_options = {'REGISTER', 'UNDO'}
	bl_description = "Toggle Visible with Selected"
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and 
			(engine in cls.COMPAT_ENGINES) and obj.data.shape_keys)
	
	def execute(self, context):
		obj = bpy.context.active_object
		active_index = obj.active_shape_key_index
		sel = get_visible_selected(obj)
		shape_keys = obj.data.shape_keys.key_blocks

		if sel:
			if len(sel) == 1:
				shape_keys[sel[0]].mute = not shape_keys[sel[0]].mute 
			else:
				# Hide other shape keys and save their states
				vis = [x for x, i in enumerate(sel) if not shape_keys[i].mute]
				if len(vis) != 1:
					for i in sel:
						shape_keys[i].mute = 1
					shape_keys[sel[0]].mute = 0
					vis = [0]
				
				vis = vis[0]
				shape_keys[sel[vis]].mute = True
				shape_keys[sel[vis - 1]].mute = False		
		return{'FINISHED'} 

class NegateShapeKey(bpy.types.Operator):
	bl_idname = "object.shape_key_negate"
	bl_label = "Negate"
	bl_description = "Negate Weight"
	bl_options = {'REGISTER', 'UNDO'}
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and 
			(engine in cls.COMPAT_ENGINES) and obj.data.shape_keys)
	
	def execute(self, context):
		obj = bpy.context.active_object
		sel = get_visible_selected(obj)
		shape_keys = obj.data.shape_keys.key_blocks
		for i in sel:
			if shape_keys[i].value >= 0:
				shape_keys[i].slider_min = -1.0
				shape_keys[i].value = -1.0
			else:
				shape_keys[i].slider_min = 0.0
				shape_keys[i].value = 1
		return{'FINISHED'} 

class ShapeKeyCopySelected(bpy.types.Operator):
	bl_idname = "object.shape_key_copy_selected"
	bl_label = "Create New Shape Key from Selected"
	bl_description = "Create New Shape Key from Selected"
	bl_options = {'REGISTER', 'UNDO'}
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	mirror = bpy.props.BoolProperty(default = False, description = "Create Mirror from Selected Shape Keys")
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and 
			(engine in cls.COMPAT_ENGINES) and obj.data.shape_keys)
	
	def execute(self, context):
		new_shape, name = shape_key_copy()
		if self.mirror:
			bpy.ops.object.shape_key_mirror()
			new_shape.name = name + "_mirrored"
		else:
			new_shape.name = name + "_copy"
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
		return True
	
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
		return True
	
	def execute(self, context):
		obj = context.object
		mesh = obj.data
		keys = mesh.shape_key_labels.keys()
		index = obj.active_shape_key_label_index
		
		if keys and (index != 0 or len(keys) == 1):
			mesh.shape_key_labels.remove(index)
			obj.active_shape_key_label_index = min(len(keys) - 2, index)
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
		return True
	
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
		return True
	
	def draw(self, context):
		pass
	
	def execute(self, context):
		obj = context.object
		mesh = obj.data
		label = mesh.shape_key_labels[self.index]
		
		# Get indexes
		label_indexes = [i.index for i in label.indexes]
		selected = get_visible_selected( obj )

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
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	from_mix = bpy.props.BoolProperty(
		name = "Add To Label From Mix",
		default = False)
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and (engine in cls.COMPAT_ENGINES))
	
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
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		if not (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and (engine in cls.COMPAT_ENGINES)):
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
			sel = get_visible_selected( obj )
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
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} 
			and (engine in cls.COMPAT_ENGINES))
		
	
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
		sel = get_visible_selected( obj )
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
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}
	
	type = bpy.props.EnumProperty(
		name="Move Shape Key Direction",
		items =	(('UP', "Up", "Up"),
				('DOWN', "Down", "Down"),
				),
		default = 'UP'
		)
	
	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and (engine in cls.COMPAT_ENGINES))
	
	def execute(self, context):
		obj = context.object
		mesh = obj.data
		index = obj.active_shape_key_label_index
		
		# Get indexes of visible keys
		indexes = get_visible_indexes(obj)
		
		# If it's a real label
		if index > 0:
			# I'm sure there's a better way to do this.
			
			# Do everything in reverse if going down
			if self.type == 'DOWN':
				indexes.reverse()
			
			# Indexes of selected keys
			pos = [indexes.index(i) for i in get_visible_selected(obj)]
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
			# Get visible and sort it
			sel = get_visible_selected(obj)
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

class MESH_MT_shape_key_view_mode(Menu):
	bl_label = "View Mode"

	def draw(self, context):
		layout = self.layout
		obj = context.object
		for item in bpy.types.Scene.shape_keys_view_mode[1]['items']:
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

	
'''----------------------------------------------------------------------------
                            Shape Key Panel
----------------------------------------------------------------------------'''

class DATA_PT_shape_keys(MeshButtonsPanel, Panel):
	bl_label = "Shape Keys"
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}

	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE', 'CURVE', 'SURFACE'} and (engine in cls.COMPAT_ENGINES))
		
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
		sub = col.column(align=True)
		sub.operator("object.shape_key_label_add", icon = 'ZOOMIN', text="")
		sub.operator("object.shape_key_label_remove", icon = 'ZOOMOUT', text="")
		
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
		sub = col.column(align=True)
		sub.operator("object.shape_key_add_to_label", icon = 'ZOOMIN', text = "").from_mix = False
		sub.operator("object.shape_key_remove_from_label", icon = 'ZOOMOUT', text = "")
		sub.operator("object.shape_key_delete", icon = 'PANEL_CLOSE', text = "")
		
		indexes = get_visible_indexes(ob)
		
		selected = get_visible_selected(ob)
		if indexes:
			sub.operator("object.shape_key_toggle", icon = 'RESTRICT_VIEW_OFF', text = '')
			sub.operator("object.shape_key_copy_selected", icon = 'PASTEDOWN', text = '')
			sub.operator("object.shape_key_copy_selected", icon = 'ARROW_LEFTRIGHT', text = '').mirror = True
			sub.operator("object.shape_key_negate", icon = 'FORCE_CHARGE', text = '')
			sub.operator("object.shape_key_axis", icon = 'MANIPUL', text = '')
		
		sub.menu("MESH_MT_shape_key_specials", icon = 'DOWNARROW_HLT', text = "")
		
		if indexes:
			row = box.row()
			
			##########################
			# SHAPE KEY VIEW MODE / COPY TO
			if ob.data.shape_key_labels and ob.active_shape_key_label_index == 0:	
				# Display view mode menu if "ALL" label is selected
				menu_name = next(item[1] for item in bpy.types.Scene.shape_keys_view_mode[1]['items'] if context.scene.shape_keys_view_mode == item[0])
				row.menu("MESH_MT_shape_key_view_mode", text = menu_name)
				row = row.split()
				
				# Filter "ALL" label by view mode
				if context.scene.shape_keys_view_mode == 'SELECTED':
					indexes = selected

				elif context.scene.shape_keys_view_mode == 'UNLABELED':
					indexes_set = set(indexes)
					for label in labels:
						for label_indexes in label.indexes:
							if label_indexes.index in indexes_set:
								indexes_set.remove(label_indexes.index)
					indexes = [i for i in indexes if i in indexes_set]
					
			row.label("Shape Keys")
			
			if ob.data.shape_key_labels and len(ob.data.shape_key_labels) > 1:	
				row = row.split()
				row.menu("MESH_MT_shape_key_copy_to_label", text = "Copy to Label")
			
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
			# SIDE COLUMN BOTTOM ICONS
			
			# A trip to photoshop gave me this.
			# However, this may break cross platform due to differences in icon size
			# A better solution would be a way to attach columns to the bottom of another element
			# But I don't believe this is possible with the current API
			
			side_icons = 6 + 5
			button_space = len(indexes) * 24 - 4 + 28 #shapekey row adds 28ish
			side_space = side_icons * 20 + 4	# This may be incorrect if side_icons is less than 4
			space = button_space - side_space
			if space > 0:
				sub = sub.column()
				sub.scale_y = space / 6.0
				sub.separator()			
			sub =  col.column(align=True)
			sub.operator("object.shape_key_move_in_label", icon = 'TRIA_UP', text = "").type = 'UP'
			sub.operator("object.shape_key_move_in_label", icon = 'TRIA_DOWN', text = "").type = 'DOWN'
			
			
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
		else:
			row = box.row(align = True)

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
	bpy.types.Object.active_shape_key_label_index = bpy.props.IntProperty( default = 0)
	
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
