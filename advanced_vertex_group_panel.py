''' Replaces the default vertex group panel with an "Advanced" one.

Adds the ability to sort vertex groups by labels.  Additional features may
be forthcoming.'''

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
from bpy.types import Menu, Panel
from .advanced_labels import *

class Advanced_Vertex_Group_Labels( Advanced_Labels):
	@property
	def labels( self ):
		return self.context.object.vertex_group_labels

	@property
	def selected_items( self ):
		return self.context.object.selected_vertex_group

	@property
	def active_index( self ):
		return self.context.object.active_vertex_group_label_index

	@active_index.setter
	def active_index( self, index ):
		self.context.object.active_vertex_group_label_index = index

	@property
	def active_item_index( self ):
		return self.context.object.vertex_groups.active_index

	@active_item_index.setter
	def active_item_index( self, index ):
		self.context.object.vertex_groups.active_index = index

	@property
	def items( self ):
		obj = self.context.object
		return obj.vertex_groups

	@property
	def view_mode( self ):
		return self.context.scene.vertex_group_view_mode

	@view_mode.setter
	def view_mode( self, mode ):
		context.scene.vertex_group_view_mode = mode.upper()

	def add_item_orig( self, **add_item_kwargs ):
		# I don't believe vertex groups have an optional parameter here yet.
		bpy.ops.object.vertex_group_add(**add_item_kwargs)

	def remove_item_orig( self, **remove_item_kwargs ):
		bpy.ops.object.vertex_group_remove( **remove_item_kwargs )

	def move_item_orig( self, **move_item_kwargs ):
		# move_item_kwargs: type = self.type
		bpy.ops.object.vertex_groups.move( **move_item_kwargs )

	def get_armature_groups( self ):
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

	def filter_view_mode( self, indexes, selected ):
		# Filter "ALL" label by view mode
		view_mode = self.view_mode
		items = self.items
		if view_mode == 'LOCKED':
			indexes = [i for i in indexes if items[i].lock_weight]
			selected = [i for i in selected if i in indexes]
		elif view_mode == 'UNLOCKED':
			indexes = [i for i in indexes if not items[i].lock_weight]
			selected = [i for i in selected if i in indexes]
		elif view_mode == 'ARMATURE':
			armature_groups = set(self.get_armature_groups())
			indexes = [i for i in indexes if i in armature_groups]
			selected = [i for i in selected if i in indexes]
		return indexes, selected

	def toggle_locked_item( self, inverse = False ):
		items = self.items
		indexes, selected = self.get_visible_item_indexes( )

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
	''' Easy access wrapper for Advanced_Vertex_Group_Labels '''
	items = Advanced_Vertex_Group_Labels().selected_items
	return [i.index for i in items]

def get_active_group():
	''' Easy access wrapper for Advanced_Vertex_Group_Labels '''
	return Advanced_Vertex_Group_Labels().active_item_index

################################
##	UI Classes - thin wrappers for Advanced_Vertex_Group_Labels
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

class VertexGroupsLabelAdd(bpy.types.Operator):
	bl_idname = "object.vertex_groups_label_add"
	bl_label = "Add Label"
	bl_description = "Add Label"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_mode = False)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).add( )
		return {'FINISHED'}

class VertexGroupsLabelRemove(bpy.types.Operator):
	bl_idname = "object.vertex_groups_label_remove"
	bl_label = "Remove Label"
	bl_description = "Remove Label"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_mode = False)

	def execute(self, context):
		copied_to = Advanced_Vertex_Group_Labels( context ).remove( )
		return {'FINISHED'}

class VertexGroupsLabelMove(bpy.types.Operator):
	bl_idname = "object.vertex_groups_label_move"
	bl_label = "Move Label"
	bl_description = "Move Label"
	bl_options = {'REGISTER', 'UNDO'}

	direction = bpy.props.EnumProperty(
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
		Advanced_Vertex_Group_Labels( context ).move( direction = self.direction )
		return {'FINISHED'}

class VertexGroupsSetIndex(bpy.types.Operator):
	bl_idname = "object.vertex_groups_set_index"
	bl_label = "Set Active Vertex Groups"
	bl_description = "Set Active Vertex Groups"
	bl_options = {'REGISTER', 'UNDO'}

	index = bpy.props.IntProperty(default = -1)
	shift = bpy.props.BoolProperty(default = False)

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)

	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).select_item( self.index, self.shift )
		return {'FINISHED'}

class VertexGroupsCopyToLabel(bpy.types.Operator):
	bl_idname = "object.vertex_groups_copy_to_label"
	bl_label = "Copy To Label"
	bl_description = "Copy To Label"
	bl_options = {'REGISTER', 'UNDO'}

	index = bpy.props.IntProperty(default = -1)

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)

	def execute(self, context):
		copied_to = Advanced_Vertex_Group_Labels( context ).copy_item( self.index )
		if copied_to is not None:
			self.report({'INFO'}, "Copied to %s" % copied_to)
		return {'FINISHED'}

class VertexGroupsAddToLabel(bpy.types.Operator):
	bl_idname = "object.vertex_groups_add_to_label"
	bl_label = "Add to Label"
	bl_description = "Add to Label"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return label_poll(context)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).add_item( )
		return {'FINISHED'}

class VertexGroupsRemoveFromLabel(bpy.types.Operator):
	bl_idname = "object.vertex_groups_remove_from_label"
	bl_label = "Remove From Label"
	bl_description = "Remove From Label"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		obj = context.object
		return label_poll(context, test_mode = False)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).remove_item( )
		return {'FINISHED'}

class VertexGroupsDelete(bpy.types.Operator):
	bl_idname = "object.vertex_groups_delete"
	bl_label = "Delete Vertex Groups"
	bl_description = "Delete Vertex Groups"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).delete_item( )
		return {'FINISHED'}

class VertexGroupsMoveInLabel(bpy.types.Operator):
	bl_idname = "object.vertex_groups_move_in_label"
	bl_label = "Move Vertex Groups"
	bl_description = "Move Vertex Groups"
	bl_options = {'REGISTER', 'UNDO'}

	direction = bpy.props.EnumProperty(
		name="Move Vertex Groups Direction",
		items =	(('UP', "Up", "Up"),
				('DOWN', "Down", "Down"),
				),
		default = 'UP'
		)

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).move_item( direction = self.direction )
		return {'FINISHED'}

class VertexGroupsToggleSelected(bpy.types.Operator):
	bl_idname = "object.vertex_groups_toggle_selected"
	bl_label = "Toggle Selected Vertex Groups"
	bl_description = "Toggle Selected Vertex Groups"
	bl_options = {'REGISTER', 'UNDO'}

	shift = bpy.props.BoolProperty(default = False)

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)

	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).toggle_selected_item( inverse = not self.shift )
		return {'FINISHED'}

class VertexGroupsToggleLocked(bpy.types.Operator):
	bl_idname = "object.vertex_groups_toggle_locked"
	bl_label = "Toggle Locked Vertex Groups"
	bl_description = "Toggle Locked Vertex Groups"
	bl_options = {'REGISTER', 'UNDO'}

	shift = bpy.props.BoolProperty(default = False)

	@classmethod
	def poll(cls, context):
		return label_poll(context, test_shapes = True, test_mode = False)

	def invoke(self, context, event):
		self.shift = event.shift
		return self.execute(context)

	def execute(self, context):
		Advanced_Vertex_Group_Labels( context ).toggle_locked_item( inverse = not self.shift )
		return {'FINISHED'}

class MESH_MT_vertex_group_view_mode(Menu):
	bl_label = "View Mode"

	def draw(self, context):
		layout = self.layout
		obj = context.object
		for item in bpy.types.Scene.vertex_group_view_mode[1]['items']:
			if item[0] == 'UNLABELED' and obj.vertex_group_labels and obj.active_vertex_group_label_index != 0:
				continue

			if item[0] != context.scene.vertex_group_view_mode:
				layout.prop_enum(context.scene, "vertex_group_view_mode", item[0])

class MESH_MT_vertex_groups_copy_to_label(Menu):
	bl_label = "Copy Vertex Group to Label"

	def draw(self, context):
		layout = self.layout
		obj = context.object
		for x, label in enumerate(obj.vertex_group_labels):
			if x > 0:
				layout.operator("object.vertex_groups_copy_to_label", icon='FILE_FOLDER', text = label.name).index = x

##################################
##	 Main UI
class DATA_PT_vertex_groups(MeshButtonsPanel, Panel):
	bl_label = "Vertex Groups"
	COMPAT_ENGINES = {'BLENDER_RENDER', 'BLENDER_GAME'}

	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		obj = context.object
		return (obj and obj.type in {'MESH', 'LATTICE'} and (engine in cls.COMPAT_ENGINES))

	def draw(self, context):
		layout = self.layout

		ob = context.object
		group = ob.vertex_groups.active

		##########################
		# LABELS LIST
		layout.label("Labels")
		row = layout.row()
		row.template_list(ob, "vertex_group_labels", ob, "active_vertex_group_label_index", rows = 4) #

		col = row.column()
		sub = col.column( align=True )
		sub.operator("object.vertex_groups_label_add", icon = 'ZOOMIN', text="")
		sub.operator("object.vertex_groups_label_remove", icon = 'ZOOMOUT', text="")


		sub =  col.column()
		sub.separator()
		sub.scale_y = 4.9

		sub =  col.column(align=True)
		sub.operator("object.vertex_groups_label_move", icon = 'TRIA_UP', text = "").direction = 'UP'
		sub.operator("object.vertex_groups_label_move", icon = 'TRIA_DOWN', text = "").direction = 'DOWN'


		labels = ob.vertex_group_labels
		if labels:
			row = layout.row()
			row.prop(labels[ob.active_vertex_group_label_index], 'name')

		##########################
		# SIDE COLUMN ICONS
		row = layout.row()
		box = row.box()
		col = row.column()
		col.separator()
		side_col = col.column(align=True)
		side_col.operator("object.vertex_groups_add_to_label", icon = 'ZOOMIN', text = "")
		side_col.operator("object.vertex_groups_remove_from_label", icon = 'ZOOMOUT', text = "")
		side_col.operator("object.vertex_groups_delete", icon = 'PANEL_CLOSE', text = "")

		side_col.menu("MESH_MT_vertex_group_specials", icon = 'DOWNARROW_HLT', text = "")
		indexes, selected = Advanced_Vertex_Group_Labels( context ).get_visible_item_indexes()

		if len(ob.vertex_groups):
			row = box.row()

			##########################
			# VIEW MODE / COPY TO
			# Display view mode menu if "ALL" label is selected
			menu_name = next(item[1] for item in bpy.types.Scene.vertex_group_view_mode[1]['items'] if context.scene.vertex_group_view_mode == item[0])
			row.menu("MESH_MT_vertex_group_view_mode", text = menu_name)
			row = row.split()

			row.label("Groups")

			if ob.vertex_group_labels and len(ob.vertex_group_labels) > 1:
				row = row.split()
				row.menu("MESH_MT_vertex_groups_copy_to_label", text = "Copy to Label")

		if indexes:
			##########################
			# VERTEX GROUP ITEMS
			for i in indexes:
				row = box.row(align = True)
				row.scale_y = 0.8
				row = row.split(percentage = 0.09)
				icon = 'PROP_OFF'
				if i == ob.vertex_groups.active_index:
					icon = 'PROP_ON'
				elif i in selected:
					icon = 'PROP_CON'
				row.operator("object.vertex_groups_set_index", icon = icon, text = '').index = i
				row = row.split(percentage = .89)
				row.prop(ob.vertex_groups[i], 'name', text = '')

				icon = 'UNLOCKED'
				if ob.vertex_groups[i].lock_weight:
					icon = 'LOCKED'
				row.prop(ob.vertex_groups[i], 'lock_weight', icon =  icon, text = '')

			##########################
			# VERTEX GROUP BOTTOM ROW TOGGLES

			row = box.row(align = True)
			row.scale_y = 0.8
			row = row.split(percentage = 0.10, align = True)
			row.operator("object.vertex_groups_toggle_selected", icon = 'PROP_ON', text = '')

			row = row.split(percentage = 0.91, align = True)
			row.label('')

			row.operator("object.vertex_groups_toggle_locked", icon = 'UNLOCKED', text = '') #.absolute = True

			##########################
			# SIDE COLUMN BOTTOM ICONS

			# A trip to photoshop gave me this.
			# However, this may break cross platform due to differences in icon size
			# A better solution would be a way to attach columns to the bottom of another element
			# But I don't believe this is possible with the current API

			side_icons =  6
			button_space = len(indexes) * 24 - 4 + 30 # + 9 #shapekey row adds 30ish, Extra bottom row as padding adds 9ish.
			side_space = side_icons * 20 + 4	# This may be incorrect if side_icons is less than 4
			space = button_space - side_space
			if space > 0:
				side_col = side_col.column()
				side_col.scale_y = space / 6.0
				side_col.separator()
			side_col =  col.column(align=True)
			side_col.operator("object.vertex_groups_move_in_label", icon = 'TRIA_UP', text = "").direction = 'UP'
			side_col.operator("object.vertex_groups_move_in_label", icon = 'TRIA_DOWN', text = "").direction = 'DOWN'

			##########################
			# THE REST OF THE DEFAULT INTERFACE
			# (Minus the name field, which I removed)

			# row = layout.row()
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
##	 Register UI
def label_index_updated(self, context):
	Advanced_Vertex_Group_Labels( context ).label_index_updated()

old_vertex_group_menu = None
def register():
	# Add rna for Mesh object, to store label names and corresponding indexes.
	bpy.types.Object.vertex_group_labels = bpy.props.CollectionProperty(type = IndexCollection)
	bpy.types.Object.selected_vertex_group = bpy.props.CollectionProperty(type = IndexProperty)
	bpy.types.Object.active_vertex_group_label_index = bpy.props.IntProperty( default = 0)

	# Replace shapekeys panel with my own
	global old_vertex_group_menu
	old_vertex_group_menu = bpy.types.DATA_PT_vertex_groups

	bpy.types.Scene.vertex_group_view_mode = bpy.props.EnumProperty(
		name="View",
		items =	(('ALL', "All", "View All Vertex Groups"),
				('ARMATURE', "Armature", "View Armature Vertex Groups"),
				('UNLABELED', "Unlabeled", "View Unlabeled Vertex Groups"),
				('LOCKED', "Locked", "View Locked Vertex Groups"),
				('UNLOCKED', "Unlocked", "View Unlocked Vertex Groups"),
				),
		)

	# try:
		# bpy.utils.register_module(__name__)
	# except Exception as err:
		# if not (err.args[0] and "defines no classes" in err.args[0]):
			# raise

def unregister():
	# bpy.utils.unregister_module(__name__)
	bpy.utils.register_class(old_vertex_group_menu)

	del bpy.types.Scene.vertex_group_view_mode

	# Should I delete the rna types created?  Hmmmm.
	# I don't want a user to lose data from reloading my addon,
	# but I also don't want extra data saved if it's permanently disabled.
	# I think the lesser evil here is not to delete data.

if __name__ == "__main__":
	register()
