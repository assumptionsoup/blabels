''' Blabels class which can be inherited from to quickly extend labels
to a ui panel in Blender. '''
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

class Blabels( object ):
	def __init__(self, context = None):
		if context is None:
			self.context = bpy.context
		else:
			self.context = context # ?? save context?  or have everything pass it around?

		# shape_key_labels = bpy.props.CollectionProperty(type = IndexCollection)
		# selected_shape_keys = bpy.props.CollectionProperty(type = IndexProperty)
		# active_shape_key_label_index = bpy.props.IntProperty( default = 0, update = label_index_updated)

	# Override these, or use the ones in init?
	# Since I once noted that saving the object to a class variable is a bad idea,
	# I'm leaning towards these.

	@property
	def labels( self ):
		raise NotImplementedError

	@property
	def selected_items( self ):
		raise NotImplementedError

	@property
	def active_index( self ):
		raise NotImplementedError

	@active_index.setter
	def active_index( self, index ):
		# May need a setter since it's not passing a complex object type (eg, might accidentally pass 23 instead of the prop reference)
		raise NotImplementedError

	@property
	def active_item_index( self ):
		raise NotImplementedError

	@active_item_index.setter
	def active_item_index( sel, index ):
		raise NotImplementedError

	@property
	def items( self ):
		raise NotImplementedError

	@property
	def view_mode( self ):
		raise NotImplementedError

	@view_mode.setter
	def view_mode( self, mode ):
		raise NotImplementedError

	def add_item_orig( self, **add_item_kwargs ):
		# Original call to add item
		raise NotImplementedError

	def remove_item_orig( self, **remove_item_kwargs ):
		# Original call to remove item
		raise NotImplementedError

	def move_item_orig( self, *move_item_kwargs ):
		# Original call to move item
		raise NotImplementedError

	# END of functiones that need overrides to work.
	def add( self ):
		obj = self.context.object
		labels = self.labels # mesh.shape_key_labels
		keys = labels.keys()
		label = labels.add()

		if not keys:
			label.name = "All"
			num_keys = len(self.items)
			format_label_name( label, num_keys)
		else:
			label.name = "Label %d" % len(keys)
			format_label_name( label )

		index = len( labels.keys() ) - 1
		self.active_index = index

	def remove( self ):
		obj = self.context.object
		labels = self.labels
		keys = labels.keys()
		index = self.active_index

		if keys and (index != 0 or len(keys) == 1):
			labels.remove(index)
			self.active_index = min(len(keys) - 2, index)

	def move( self, direction = 'up' ):
		# Gather data
		obj = self.context.object
		mesh = obj.data
		labels = self.labels
		keys = labels.keys()
		index = self.active_index

		# Check for labels.  Don't move special label "ALL".
		if keys and index > 0:
			if direction.lower() == 'up':
				if index - 1 > 0:
					labels.move(index, index - 1)
					self.active_index = index - 1
			else:
				if index + 1 < len(keys):
					labels.move(index, index + 1)
					self.active_index = index + 1

	def select_item( self, index, add = False ):
		if index > -1:
			sel = self.selected_items

			if not add:
				# Clear selected if shift isn't used
				for x in range(len(sel)):
					sel.remove(0)
			else:
				for x, key in enumerate(sel):
					# Clicked twice - deselect
					if index == key.index:
						if self.active_item_index == index:
							# Adjust active index.
							if len(sel) > 1:
								sel.remove(x)
								self.active_item_index = sel[-1].index
						else:
							sel.remove(x)
						return

			# Set active
			self.active_item_index = index

			# Add to selected
			i = sel.add()
			i.index = index

	# Item related - Might move these to a different class.

	def get_visible_selection( self, indexes ):
		# Get selected
		selected = [i.index for i in self.selected_items]
		if not selected:
			selected = [self.active_item_index]
		selected = set(selected)

		return [i for i in indexes if i in selected]

	def get_visible_item_indexes( self, skip_view_mode_filter = False ):
		# Get visible shape key indexes
		labels = self.labels
		items = self.items
		index = self.active_index
		indexes = []

		if index != 0 and labels and len(labels):
			# Invalid State Check (only fixes out of range states)
			item_indexes = labels[index].indexes
			for x in reversed(range(len(item_indexes))):
				if item_indexes[x].index >= len(items):
					item_indexes.remove(x)

			# Find indexes in label
			indexes = [i.index for i in item_indexes if i.index > -1]
		else:
			indexes = [i for i in range(len(items))]

		selected = []
		if indexes:
			selected = self.get_visible_selection(indexes)
			if not skip_view_mode_filter:
				view_mode = self.view_mode
				if view_mode == 'SELECTED':
					indexes = selected[:]
				elif view_mode == 'UNLABELED':
					indexes_set = set(indexes)
					labels = self.labels
					for label in labels:
						for label_indexes in label.indexes:
							if label_indexes.index in indexes_set:
								indexes_set.remove(label_indexes.index)
							if not indexes_set:
								break
						if not indexes_set:
							break
					indexes = [i for i in indexes if i in indexes_set]
					selected = [i for i in selected if i in indexes]
				else:
					indexes, selected = self.filter_view_mode( indexes, selected )
		return indexes, selected

	def copy_item( self, label_index ):
		''' Copies selected items to the given label index.
		Returns True if an item was added. '''
		label = self.labels[label_index]

		# Get indexes
		item_indexes = [i.index for i in label.indexes]
		selected = self.get_visible_item_indexes()[1]

		# Only add indexes that aren't already in that label
		added_indexes = False
		for i in selected:
			if i not in item_indexes:
				added_indexes = True
				indexes = label.indexes.add()
				indexes.index = i

		if added_indexes:
			format_label_name(label)

		if added_indexes:
			return strip_label_number(label)
		return None

	def add_item( self, **add_items_kwargs ):
		index = self.active_index
		labels =  self.labels

		self.add_item_orig( **add_items_kwargs )

		# Add to current label if on is selected.
		if index > 0:
			label = labels[index]
			label_index = label.indexes.add()
			label_index.index = self.active_item_index
			format_label_name(label)

		# Update "All" Label
		if labels:
			num_items = len(self.items)
			format_label_name(labels[0], num_items)

		# Update selected
		selected_items = self.selected_items
		for x in range(len(selected_items)):
			selected_items.remove(0)
		selected_index = selected_items.add()
		selected_index.index = self.active_item_index

	def remove_item_index_from_label( self, index, label ):
		for x, i in enumerate(label.indexes):
			if index == i.index:
				label.indexes.remove(x)
				format_label_name( label )
				break

	def remove_item( self ):
		index = self.active_index
		if index > 0:
			label = self.labels[index]

			# get selected
			sel = self.get_visible_item_indexes( )[1]
			sel.sort()
			sel.reverse()
			for i in sel:
				self.remove_item_index_from_label( i, label )

	def _delete_active_item(self):
		labels = self.labels
		item_index = self.active_item_index
		self.remove_item_orig()

		if labels:
			# Update "All" Label
			num_keys = len(self.items)
			format_label_name( labels[0], num_keys)

			# Update other labels
			if len(labels) > 1:
				for x in range(1, len(labels)):
					self.remove_item_index_from_label(item_index, labels[x])

				# Correct the moved index in every label (except the first label, All)
				for x in range(1, len(labels)):
					label_indexes = labels[x].indexes
					for label_index in label_indexes:
						if label_index.index >= item_index:
							label_index.index -= 1

	def delete_item( self ):
		# Delete selected
		sel = self.get_visible_item_indexes( )[1]
		if sel:
			sel.sort()
			sel.reverse()
			for i in sel:
				self.active_item_index = i
				self._delete_active_item( )

			# Update active index
			active_index = self.active_item_index
			if len(self.items) > active_index + 1:
				self.active_item_index = active_index + 1

			# Update selected
			selected_items = self.selected_items
			for sel in selected_items:
				selected_items.remove(0)
			s = selected_items.add()
			s.index = self.active_item_index

	def move_item( self, direction = 'up' ): #move_in_label(self):
		label_index = self.active_index
		labels = self.labels

		# Get indexes of visible keys
		indexes, sel = self.get_visible_item_indexes()

		# If it's a real label
		if label_index > 0:
			# I'm sure there's a better way to do this.

			# Do everything in reverse if going down
			if direction.lower() != 'up':
				indexes.reverse()

			# Indexes of selected keys
			pos = [indexes.index(i) for i in sel]
			pos.sort()

			# Indexes are in order, beginning at 0, and therefore at the start of the list
			# and can be skipped
			if pos == list(range(len(pos))):
				return

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
			if direction.lower() != 'up':
				new_indexes.reverse()

			# Apply changes
			for x, i in enumerate(new_indexes):
				labels[label_index].indexes[x].index = i
		else:
			# Sort visible
			sel.sort()

			# Reverse it if going down to help with clashes
			increment = -1
			if direction.lower() != 'up':
				sel.reverse()
				increment = 1

			item_index = self.active_item_index
			new_item_index = -1
			for x, i in enumerate(sel):
				# Only move down if it won't run into another selected item
				if (i + increment) not in sel:
					# Set active index, move shape key
					self.active_item_index = i
					self.move_item_orig( self, direction = direction.upper() )
					new_index = self.active_item_index

					# Update actual selection
					selected_items = self.selected_items
					selected_items[x].index = new_index

					# Update selected items, so item clashes resolve correctly
					sel[x] = new_index

					# Save active_index, so it can be restored correctly later
					if i == item_index:
						new_item_index = new_index

					# Correct the moved index in every label (except the first label, All)
					if len(labels) > 1:
						for y in range(1, len(labels)):
							label_indexes = labels[y].indexes
							for label_index in label_indexes:
								if label_index.index == i:
									label_index.index = new_index
								elif label_index.index == new_index:
									label_index.index = i
			# Restore active_index
			if new_item_index > -1:
				self.active_item_index = new_item_index

	def toggle_selected_item( self, inverse = False ): #toggle_selected(self):
		selected_items = self.selected_items
		actual_indexes, actual_selected = self.get_visible_item_indexes( skip_view_mode_filter = True )

		# Clean selected
		for x in range(len(selected_items)):
			selected_items.remove(0)

		if inverse:
			# Select or de-select all
			if len(actual_selected) >= 0 and len(actual_selected) != len(actual_indexes):
				for i in actual_indexes:
					index = selected_items.add()
					index.index = i
		else:
			# Inverse selection
			actual_selected = set(actual_selected)
			for i in actual_indexes:
				if i not in actual_selected:
					index = selected_items.add()
					index.index = i

		# Correct active index.  Correct for 0 selected.
		selected = [i.index for i in selected_items]
		if selected:
			if self.active_item_index not in selected:
				self.active_item_index = selected[-1]
		else:
			self.active_item_index = 0
			index = selected_items.add()
			index.index = 0

	def label_index_updated(self):
		if self.labels and self.view_mode == 'UNLABELED' and self.active_index != 0:
			self.view_mode = 'ALL'

# Taken from blender ui files.  Needed when Blabels is eventaully put into a UI class.
class MeshButtonsPanel():
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = 'data'

	@classmethod
	def poll(cls, context):
		engine = context.scene.render.engine
		return context.mesh and (engine in cls.COMPAT_ENGINES)


# Shape_Key_Blabels().add()
# Shape_Key_Blabels().remove()
# Shape_Key_Blabels().add()
# Shape_Key_Blabels().move('up')
# Shape_Key_Blabels().move('up')
# Shape_Key_Blabels().move('up')
# Shape_Key_Blabels().move('down')
# Shape_Key_Blabels().move('down')
# Shape_Key_Blabels().add_item()
# Shape_Key_Blabels().add_item()
# Shape_Key_Blabels().add_item()
# Shape_Key_Blabels().delete_item()
# Shape_Key_Blabels().move_item('up')
# Shape_Key_Blabels().move_item('up')
# Shape_Key_Blabels().move_item('down')

#Shape_Key_Blabels().copy_item(14)
# Shape_Key_Blabels().select_item(138)


class IndexProperty(bpy.types.PropertyGroup):
	index = bpy.props.IntProperty( default = -1)

class IndexCollection(bpy.types.PropertyGroup):
	indexes = bpy.props.CollectionProperty(type = IndexProperty)

# I wish I knew how to extend existing operators like object.shape_key_move
# So I could override those with mine, and not risk my label state machine
# becoming invalid if some other script/user calls object.shape_key_move
# instead of object.shape_key_move_to_label

# view_mode_prop = bpy.props.EnumProperty(
		# name="View",
		# items =	(('ALL', "All", "View All Shape Keys"),
				# ('UNLABELED', "Unlabeled", "View Unlabeled Shape Keys"),
				# ('SELECTED', "Selected", "View Selected Shape Keys"),
				# ('VISIBLE', "Visible", "View Visible Shape Keys"),
				# ('HIDDEN', "Hidden", "View Hidden Shape Keys"),
				# ),
		# )

# def label_index_updated( self, context ):
	# Blabels( context ).label_index_updated()

# bpy.utils.register_class(IndexProperty)
# bpy.utils.register_class(IndexCollection)

# label_prop = bpy.props.CollectionProperty(type = IndexCollection)
# selected_item_prop = bpy.props.CollectionProperty(type = IndexProperty)
# active_index_prop = bpy.props.IntProperty( default = 0, update = label_index_updated)
