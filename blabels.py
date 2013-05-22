''' Blabels class which can be inherited from to quickly extend labels
to a ui panel in Blender. '''
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
from bpy.types import Menu, UIList
from . import metamagic
import inspect


class ui_object(metamagic.CachedRegister):
    register_name = 'ui_object'


class BlenderUIRegister(object, metaclass=metamagic.RegisteringType):

    def install(self):
        self.ui = {}
        for method in self.ui_object.keys():
            self.ui[method] = getattr(self, method)

    def register(self):
        for name, blabel_operator in self.ui.items():
            ui_object = blabel_operator.ui_object
            if inspect.isclass(ui_object):
                bpy.utils.register_class(ui_object)

    def unregister(self):
        for blabel_operator in self.ui.values():
            ui_object = blabel_operator.ui_object
            if inspect.isclass(ui_object):
                bpy.utils.unregister_class(ui_object)


class BlabelUIObject(str):
    '''
    Container class for blender ui objects.

    Written because the __str__ method can't be overwritten in ui
    classes, and because functions which use ui objects expect a string
    instance.
    '''
    def __new__(cls, ui_object, name):
        obj = super().__new__(cls, name)
        obj.ui_object = ui_object
        return obj


class Blabels(object):
    def __init__(self, context=None):
        if context is None:
            self.context = bpy.context
        else:
            self.context = context

    @property
    def name(self):
        '''Name of Blabel'''
        raise NotImplementedError

    @property
    def labels(self):
        '''All labels'''
        raise NotImplementedError

    @property
    def labels_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the labels prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        raise NotImplementedError

    @property
    def selected_items_prop(self):
        '''Selected items in the active label'''
        raise NotImplementedError

    @property
    def selected_items_prop_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the selected label items prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        raise NotImplementedError

    @property
    def active_label_index(self):
        '''Active label index getter'''
        raise NotImplementedError

    @active_label_index.setter
    def active_label_index(self, index):
        '''Active label index setter'''
        # May need a setter since it's not passing a complex object type
        # (eg, might accidentally pass 23 instead of the prop reference)
        raise NotImplementedError

    @property
    def active_label_index_metadata(self):
        '''Returns a dict containing metadata needed for low level
        access to the active label index prop.

        Required dict keys:
        'attr': string name of the prop
        'source': active blender object the prop is on
        'prop': the blender property object
        '''
        raise NotImplementedError

    @property
    def active_item_index(self):
        '''Active item index'''
        raise NotImplementedError

    @active_item_index.setter
    def active_item_index(sel, index):
        '''Active item index setter'''
        raise NotImplementedError

    @property
    def items(self):
        '''All items in all labels'''
        raise NotImplementedError

    @property
    def view_mode(self):
        raise NotImplementedError

    @view_mode.setter
    def view_mode(self, mode):
        raise NotImplementedError

    @property
    def view_mode_items(self):
        '''Options that view mode can be set to.'''
        raise NotImplementedError

    def add_item_orig(self, **add_item_kwargs):
        # Original call to add item
        raise NotImplementedError

    def remove_item_orig(self, **remove_item_kwargs):
        # Original call to remove item
        raise NotImplementedError

    def move_item_orig(self, *move_item_kwargs):
        #Original call to move item
        raise NotImplementedError

    # END of functions that need overrides to work.
    def get_item_index(self, item):
        '''Return the index of the given item'''
        return self.items.index(item)

    @property
    def active_item(self):
        return self.items[self.active_item_index]

    @property
    def active_label(self):
        if self.labels:
            return self.labels[self.active_label_index]
        else:
            return None

    def get_label_items(self, index=None):
        if index is None:
            index = self.active_label_index

        label = self.labels[index]
        if index == 0:
            return self.items
        else:
            items = []
            for i in label.indexes:
                try:
                    items.append(self.items[i.index])
                except IndexError:
                    continue
            return items

    def get_num_items(self, index=None):
        if index is None:
            index = self.active_label_index

        label = self.labels[index]
        if index == 0:
            return len(self.items)
        else:
            return len(label.indexes)

    def add(self):
        labels = self.labels
        keys = labels.keys()
        label = labels.add()

        if not keys:
            label.name = "All"
        else:
            label.name = "Label %d" % len(keys)

        index = len(labels.keys()) - 1
        self.active_label_index = index

    def remove(self):
        labels = self.labels
        keys = labels.keys()
        index = self.active_label_index

        if keys and (index != 0 or len(keys) == 1):
            labels.remove(index)
            self.active_label_index = min(len(keys) - 2, index)

    def move(self, direction='up'):
        # Gather data
        labels = self.labels
        keys = labels.keys()
        index = self.active_label_index

        # Check for labels.  Don't move special label "ALL".
        if keys and index > 0:
            if direction.lower() == 'up':
                if index - 1 > 0:
                    labels.move(index, index - 1)
                    self.active_label_index = index - 1
            else:
                if index + 1 < len(keys):
                    labels.move(index, index + 1)
                    self.active_label_index = index + 1

    def select_item(self, index, add=False):
        if index > -1:
            sel = self.selected_items_prop

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


    def get_visible_selection(self, indexes):
        # Get selected
        selected = [i.index for i in self.selected_items_prop]
        if not selected:
            selected = [self.active_item_index]
        selected = set(selected)
        return [i for i in indexes if i in selected]

    def filter_view_mode(self, indexes):
        # Filter "ALL" label by view mode
        view_mode = self.view_mode.lower()
        items = self.items
        if view_mode == 'selected':
            indexes = self.get_visible_selection(indexes)
        elif view_mode == 'unlabeled':
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
        return indexes

    def get_item_indexes(self):
        ''' Find indexes of items in the active label.'''

        indexes = []
        if self.active_label_index != 0 and self.labels and len(self.labels):
            indexes = [i.index for i in self.active_label.indexes if i.index > -1]
        else:
            indexes = [i for i in range(len(self.items))]

        # Update cache whenever called
        self._all_item_indexes = indexes
        return indexes

    def get_visible_item_indexes(self, skip_view_mode_filter=False):
        '''Get visible shape key indexes.'''
        indexes = self.get_item_indexes()

        if indexes and not skip_view_mode_filter:
            indexes = self.filter_view_mode(indexes)
        selected = self.get_visible_selection(indexes)

        # Update cache whenever called
        self._visible_item_indexes = indexes
        self._selected_item_indexes = selected
        return indexes, selected

    def get_visible_items(self):
        all_indexes, selected_indexes = self.get_visible_item_indexes()
        all_items = [self.items[i] for i in all_indexes]
        selected_items = [self.items[i] for i in selected_indexes]
        return all_items, selected_items

    @property
    def visible_item_indexes(self):
        try:
            return self._visible_item_indexes
        except AttributeError:
            self.update_cache(indexes=True)
            return self._visible_item_indexes

    @property
    def selected_item_indexes(self):
        try:
            return self._selected_item_indexes
        except AttributeError:
            self.update_cache(indexes=True)
            return self._selected_item_indexes

    @property
    def visible_items(self):
        return [self.items[i] for i in self.visible_item_indexes]

    @property
    def selected_items(self):
        return [self.items[i] for i in self.selected_item_indexes]

    @property
    def all_item_indexes(self):
        try:
            return self._all_item_indexes
        except AttributeError:
            self.update_cache(indexes=True)
            return self._all_item_indexes

    @property
    def all_selected_item_indexes(self):
        try:
            return self._all_selected_item_indexes
        except AttributeError:
            self.update_cache(indexes=True)
            return self._all_selected_item_indexes

    def update_cache(self, indexes=True):
        # get_visible_item_indexes will cache it's results in
        # _selected_item_indexes and _visible_item_indexes.
        # Additionally, it will make a call to get_item_indexes which
        # will cache _all_item_indexes.
        self.get_visible_item_indexes()

        # The only variable not cached in the chain above:
        self._all_selected_item_indexes = self.get_visible_selection(self._all_item_indexes)

    def copy_item(self, label_index):
        ''' Copies selected items to the given label index.
        Returns True if an item was added. '''
        label = self.labels[label_index]

        # Get indexes
        item_indexes = [i.index for i in label.indexes]
        selected = self.selected_item_indexes

        # Only add indexes that aren't already in that label
        added_indexes = False
        for i in selected:
            if i not in item_indexes:
                added_indexes = True
                indexes = label.indexes.add()
                indexes.index = i

        if added_indexes:
            return label.name
        return None

    def add_item(self, **add_items_kwargs):
        index = self.active_label_index
        labels = self.labels

        self.add_item_orig(**add_items_kwargs)

        # Add to current label if on is selected.
        if index > 0:
            label = labels[index]
            label_index = label.indexes.add()
            label_index.index = self.active_item_index

        # Update "All" Label

        # Update selected
        selected_items = self.selected_items_prop
        for x in range(len(selected_items)):
            selected_items.remove(0)
        selected_index = selected_items.add()
        selected_index.index = self.active_item_index

    def remove_item_index_from_label(self, index, label):
        for x, i in enumerate(label.indexes):
            if index == i.index:
                label.indexes.remove(x)
                break

    def remove_item(self):
        if self.active_label_index > 0:
            for i in sorted(self.selected_item_indexes, reverse=1):
                self.remove_item_index_from_label(i, self.active_label)

    def _delete_active_item(self):
        labels = self.labels
        item_index = self.active_item_index
        self.remove_item_orig()

        if not labels:
            return

        if len(labels) > 1:
            for x in range(1, len(labels)):
                self.remove_item_index_from_label(item_index, labels[x])

            # Correct the moved index in every label (except the first label, All)
            for x in range(1, len(labels)):
                label_indexes = labels[x].indexes
                for label_index in label_indexes:
                    if label_index.index >= item_index:
                        label_index.index -= 1

    def delete_item(self):
        # Delete selected
        sel = sorted(self.selected_item_indexes, reverse=1)
        if sel:
            for i in sel:
                self.active_item_index = i
                self._delete_active_item()

            # Update active index
            active_label_index = self.active_item_index
            if len(self.items) > active_label_index + 1:
                self.active_item_index = active_label_index + 1

            # Update selected
            selected_items = self.selected_items_prop
            for sel in selected_items:
                selected_items.remove(0)
            s = selected_items.add()
            s.index = self.active_item_index

    def move_item(self, direction='up'):
        label_index = self.active_label_index
        labels = self.labels

        # Get indexes of visible keys
        indexes = self.visible_item_indexes
        sel = self.selected_item_indexes

        # If it's a real label
        if label_index > 0:
            # I'm sure there's a better way to do this.
            # Do everything in reverse if going down
            if direction.lower() != 'up':
                indexes.reverse()

            # Indexes of selected keys
            pos = [indexes.index(i) for i in sel]
            pos.sort()

            # Indexes are in order, beginning at 0, and therefore at the
            # start of the list and can be skipped
            if pos == list(range(len(pos))):
                return

            # Move selections that are at the beginning of the list out
            # of the operation.
            new_indexes = []
            while pos and pos[0] == 0:
                new_indexes.append(indexes.pop(0))
                pos = [pos[y] - 1 for y in range(1, len(pos))]

            # The main logic
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
                    self.move_item_orig(direction=direction.upper())
                    new_index = self.active_item_index

                    # Update actual selection
                    selected_items = self.selected_items_prop
                    selected_items[x].index = new_index

                    # Update selected items, so item clashes resolve correctly
                    sel[x] = new_index

                    # Save active_label_index, so it can be restored correctly later
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
            # Restore active_label_index
            if new_item_index > -1:
                self.active_item_index = new_item_index

    def toggle_selected_item(self, inverse=False):
        selected_items = self.selected_items_prop
        actual_indexes = self.all_item_indexes
        actual_selected = self.all_selected_item_indexes

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
        if self.labels and self.view_mode.lower() == 'unlabeled' and self.active_label_index != 0:
            self.view_mode = 'All'

        # Invalid State Check (only fixes out of range states)

        # This is only safe to perform here because this method is meant
        # to be called from a callback - not directly from within the UI
        # (which would give an invalid context error)
        labels = self.labels
        items = self.items
        index = self.active_label_index

        if index != 0 and labels and len(labels):
            item_indexes = labels[index].indexes
            for x in reversed(range(len(item_indexes))):
                if item_indexes[x].index >= len(items):
                    item_indexes.remove(x)

def build_operator(name, idname, label=None, description=None,
                   options={'REGISTER', 'UNDO'},
                   poll_func=None, execute_func=None, invoke_func=None,
                   members=None):
    if members is None:
        members = {}
    if members.get('bl_idname', None) is None:
        members['bl_idname'] = idname
    if description is not None and members.get('bl_description', None) is None:
        members['bl_description'] = description
    if label is not None and members.get('bl_label', None) is None:
        members['bl_label'] = label
        if description is None and members.get('bl_description', None) is None:
            members['bl_description'] = label
    if members.get('bl_options', None) is None:
        members['bl_options'] = options

    if poll_func is not None and members.get('poll', None) is None:
        @classmethod
        def poll(cls, context):
            return poll_func(cls, context)
        members['poll'] = poll

    if execute_func is not None and members.get('execute', None) is None:
        def execute(self, context):
            result = execute_func(self, context)
            if result is None:
                return {'FINISHED'}
            else:
                return result
        members['execute'] = execute

    if invoke_func is not None and members.get('invoke', None) is None:
        def invoke(self, context, event):
            result = invoke_func(self, context, event)
            if result is None:
                return self.execute(context)
            else:
                return result
        members['invoke'] = invoke

    opclass = type(name, (bpy.types.Operator,), members)
    return opclass


class BlabelOperators(BlenderUIRegister):
    poll_modes = ['EDIT_MESH']
    poll_types = ['MESH', 'LATTICE', 'CURVE', 'SURFACE']
    poll_engines = ['BLENDER_RENDER', 'BLENDER_GAME']

    def __init__(self, blabel_class, base_name=None):
        self.bl_class = blabel_class
        if base_name is None:
            base_name = "object.%s" % self.bl_class().name
        self.base_name = base_name
        self.install()

    def poll(self, context, test_items=False, test_context=False):
        obj = context.object
        if not (obj and (self.poll_types is False or obj.type in self.poll_types) and
                (self.poll_engines is False or context.scene.render.engine in self.poll_engines)):
            return False

        if test_context and context.mode in self.context_modes:
            return False

        if test_items:
            return bool(self.bl_class(context).items)

        return True

    def blabel_operator(self, blabel_name=None, name=None, idname=None, test_context=False, test_items=False, **kwargs):
        if kwargs.get('poll_func', None) is None:
            kwargs['poll_func'] = lambda opr_self, context: self.poll(context, test_context=test_context, test_items=test_items)

        if blabel_name is not None:
            name = self.bl_class().name.split('_')
            name += blabel_name.split('_')
            name = ''.join(n.capitalize() for n in name)
            idname = "%s_%s" % (self.base_name, blabel_name)
        else:
            assert name is not None
            assert idname is not None

        return BlabelUIObject(build_operator(name, idname, **kwargs), idname)

    @ui_object
    def label_add(self):
        operator = self.blabel_operator(
            blabel_name="label_add",
            label="Add Label",
            execute_func=lambda opr_self, context: self.bl_class(context).add())
        return operator

    @ui_object
    def label_remove(self):
        operator = self.blabel_operator(
            blabel_name="label_remove",
            label="Remove Label",
            execute_func=lambda opr_self, context: self.bl_class(context).remove())
        return operator

    @ui_object
    def label_move(self):
        def poll(opr_self, context):
            if not self.poll(context):
                return False

            if self.bl_class(context).active_label_index == 0:
                return False
            return True

        direction = bpy.props.EnumProperty(
            name="Move Label Direction",
            items=(
                ('UP', "Up", "Up"),
                ('DOWN', "Down", "Down"),),
            default='UP')

        operator = self.blabel_operator(
            blabel_name="label_move",
            label="Move Label",
            execute_func=lambda opr_self, context: self.bl_class(context).move(direction=opr_self.direction),
            poll_func=poll,
            members={'direction': direction})

        return operator

    @ui_object
    def item_set_index(self):
        index = bpy.props.IntProperty(default=-1)
        shift = bpy.props.BoolProperty(default=False)

        def invoke(opr_self, context, event):
            opr_self.shift = event.shift

        operator = self.blabel_operator(
            blabel_name="set_index",
            label="Set Active Item",
            execute_func=lambda opr_self, context: self.bl_class(context).select_item(opr_self.index, opr_self.shift),
            invoke_func=invoke,
            members={'index': index, 'shift': shift},
            test_items=True)

        return operator

    @ui_object
    def item_add(self):
        operator = self.blabel_operator(
            blabel_name="add_to_label",
            label="Add Item",
            execute_func=lambda opr_self, context: self.bl_class(context).add_item())
        return operator

    @ui_object
    def item_add_to_label(self):
        index = bpy.props.IntProperty(default=-1)

        def execute(opr_self, context):
            copied_to = self.bl_class(context).copy_item(opr_self.index)
            if copied_to is not None:
                opr_self.report({'INFO'}, "Copied to %s" % copied_to)

        operator = self.blabel_operator(
            blabel_name="copy_to_label",
            label="Add To Label",
            execute_func=execute,
            members={'index': index},
            test_items=True)

        return operator

    @ui_object
    def item_remove(self):
        def poll(cls, context):
            if not self.poll(context):
                return False

            obj = context.object
            labels = self.bl_class(context).labels
            index = self.bl_class(context).active_label_index
            return (labels and index > 0)

        operator = self.blabel_operator(
            blabel_name="remove_from_label",
            label="Remove From Label",
            execute_func=lambda oper_self, context: self.bl_class(context).remove_item(),
            poll_func=poll)

        return operator

    @ui_object
    def item_delete(self):

        # Querying visible items is a somewhat intensive task, so I'm on
        # the hedge performance-wise whether to use this poll method.
        # The delete operation will only delete visible indexes, so this
        # is purely for anesthetics and maintaining a consistent ui.

        def poll(cls, context):
            if not self.poll(context):
                return False

            return bool(self.bl_class(context).visible_item_indexes)

        operator = self.blabel_operator(
            blabel_name="delete",
            label="Delete Item",
            execute_func=lambda oper_self, context: self.bl_class(context).delete_item(),
            poll_func = poll,
            test_items=True)

        return operator

    @ui_object
    def item_move(self):
        direction = bpy.props.EnumProperty(
            name="Move Item Direction",
            items = (
                        ('UP', "Up", "Up"),
                        ('DOWN', "Down", "Down"),
                   ),
            default = 'UP'
           )

        operator = self.blabel_operator(
            blabel_name="move_in_label",
            label="Move Item",
            execute_func=lambda oper_self, context: self.bl_class(context).move_item(direction=oper_self.direction),
            members={'direction': direction},
            test_items=True)

        return operator

    @ui_object
    def item_toggle_select(self):
        shift = bpy.props.BoolProperty(default=False)

        def invoke_func(opr_self, context, event):
            opr_self.shift = event.shift

        operator = self.blabel_operator(
            blabel_name="toggle_selected",
            label="Toggle Selected Item",
            execute_func=lambda opr_self, context: self.bl_class(context).toggle_selected_item(inverse=not opr_self.shift),
            invoke_func=invoke_func,
            members={'shift': shift},
            test_items=True)

        return operator

    @ui_object
    def label_list(self):
        name = self.bl_class().name.split('_')
        name = ''.join(n.capitalize() for n in name)
        name = 'UI_UL_%s' % name

        def draw_item(ui_self, context, layout, data, item, icon, active_data, active_propname, index):
            label = self.bl_class(context).labels[index]
            num_items = self.bl_class(context).get_num_items(index)
            num_items = str(num_items)

            layout = layout.split(percentage=0.8)
            layout.label(text=label.name, translate=False, icon_value=icon)
            layout.label(text=num_items)

        ui_list_class = type(name, (UIList,), {'draw_item': draw_item})
        return BlabelUIObject(ui_list_class, name)

    @property
    def view_mode_items(self):
        items = [
                ('All', "All", "View All Vertex Groups"),
                ('Selected', "Selected", "View Selected Vertex Groups"),
                ('Unlabeled', "Unlabeled", "View Unlabeled Vertex Groups"),
                ]
        return items

    @ui_object
    def view_mode_prop(self):
        bpy.types.Scene.blabel_view_mode = bpy.props.EnumProperty(
            name="View",
            items = self.view_mode_items)
        return BlabelUIObject(bpy.types.Scene.blabel_view_mode, 'bpy.types.Scene.blabel_view_mode')

    @ui_object
    def view_mode(self):
        name = self.bl_class().name.split('_')
        name = ''.join(n.capitalize() for n in name)
        name = '%sViewMode' % name

        propAttr = self.view_mode_prop.ui_object[1]['attr']
        def draw(ui_self, context):
            blabel = self.bl_class(context)
            layout = ui_self.layout
            obj = context.object
            for item in self.view_mode_items:
                item = item[0].lower()
                if item == 'unlabeled' and blabel.labels and blabel.active_label_index != 0:
                    continue

                if item != blabel.view_mode.lower():
                    layout.prop_enum(context.scene, propAttr, item.capitalize())

        view_mode_class = type(name, (Menu,), {'draw': draw, 'bl_label': "View Mode"})
        return BlabelUIObject(view_mode_class, name)

    @ui_object
    def add_to_label_menu(self):
        name = self.bl_class().name.split('_')
        name = ''.join(n.capitalize() for n in name)
        name = '%sCopyToLabelMenu' % name

        bl_label = "Copy Item to Label"

        def draw(ui_self, context):
            layout = ui_self.layout
            obj = context.object

            for x, label in enumerate(self.bl_class(context).labels):
                if x > 0:
                    layout.operator(self.item_add_to_label, icon='FILE_FOLDER', text=label.name).index = x

        copy_class = type(name, (Menu,), {'draw': draw, 'bl_label': bl_label})
        return BlabelUIObject(copy_class, name)


    @ui_object
    def null(self):
        def poll(cls, context):
            return True

        def execute(self, context):
            return {'FINISHED'}

        operator = self.blabel_operator(
            blabel_name="null",
            label="",
            execute_func=execute,
            poll_func=poll,
            members={'bl_icon': 'BLANK1',
                     'bl_options': {'REGISTER'}})
        return operator



def prepost_calls(func):
    def wrapped(self, *args, **kwargs):
        if func.__name__ not in self.prepost_calls:
            self.prepost_calls.add(func.__name__)
            pre_func = getattr(self, '_pre_%s' % func.__name__)
            pre_func(*args, **kwargs)
            results = func(self, *args, **kwargs)
            post_func = getattr(self, '_post_%s' % func.__name__)
            post_func(*args, **kwargs)
            self.prepost_calls.remove(func.__name__)
        else:
            results = func(self, *args, **kwargs)
        return results
    return wrapped


class BaseBlabelList(object):

    def __init__(self, context, layout, blabel, operators, name):
        self.context = context
        self.layouts = {'main': layout}
        self.blabel = blabel(context)
        self.operators = operators
        self.items = []
        self.selected = []
        self.name = name
        self.num_top_sidebar_items = 0
        self.num_bottom_sidebar_items = 2
        self.prepost_calls = set([])

    @property
    def num_rows(self):
        return len(self.items)

    def _pre_draw_items(self): pass
    def _post_draw_items(self): pass

    @prepost_calls
    def draw_items(self):
        for x, item in enumerate(self.items):
            self.layouts['item_row'] = self.layouts['items_column'].row()
            self.draw_item(item)

    def _pre_draw_item(self, item): pass
    def _post_draw_item(self, item): pass

    @prepost_calls
    def draw_item(self, item):
        pass

    def _pre_draw_sidebar_top(self): pass
    def _post_draw_sidebar_top(self):
        lines = self.num_rows - self.num_top_sidebar_items - self.num_bottom_sidebar_items
        for x in range(lines):
            self.layouts['sidebar'].label('', icon='BLANK1')

    @prepost_calls
    def draw_sidebar_top(self):
        pass

    def _pre_draw_sidebar_bottom(self):pass
    def _post_draw_sidebar_bottom(self): pass

    @prepost_calls
    def draw_sidebar_bottom(self):
        pass

    def _pre_draw_sidebar_item(self, item): pass
    def _post_draw_sidebar_item(self, item): pass

    @prepost_calls
    def draw_sidebar_item(self, item):
        pass

    def draw_items_layout(self):
        # Split it up
        layouts = self.layouts
        layouts['items_box'] = layouts['base'].box()
        layouts['items_column'] = layouts['items_box'].column(align=True)
        layouts['sidebar'] = layouts['base'].column(align=True)

    def draw(self):
        '''Main draw method'''
        layouts = self.layouts

        # Main label
        layouts['name_label'] = layouts['main'].row()
        layouts['name_label'].label(self.name.capitalize())

        # List + Sidebar body
        layouts['base'] = layouts['main'].row()

        # Split it up
        self.draw_items_layout()

        # Draw it all
        self.draw_items()
        self.draw_sidebar_top()
        self.draw_sidebar_bottom()
        layouts['items_box'].row(align=True)


class BlabelLabelList(BaseBlabelList):
    def __init__(self, context, layout, blabel, operators, name='Labels', max_rows=6):
        super().__init__(context, layout, blabel, operators, name)
        self.items = self.blabel.labels
        self.selected = self.blabel.active_label
        self.max_rows = max_rows

    @property
    def num_rows(self):
        return min(self.max_rows, len(self.items))

    def draw_items_layout(self):
        # Split it up
        layouts = self.layouts
        if self.items:
            layouts['items_box'] = layouts['base'].column()
        else:
            layouts['items_box'] = self.layouts['base'].box()
        layouts['items_column'] = layouts['items_box'].column(align=True)
        layouts['sidebar'] = layouts['base'].column(align=True)

    @prepost_calls
    def draw_items(self):
        if self.items:
            self.layouts['items_box'].template_list(
                self.operators.label_list,
                '',
                self.blabel.labels_metadata['source'],
                self.blabel.labels_metadata['attr'],
                self.blabel.active_label_index_metadata['source'],
                self.blabel.active_label_index_metadata['attr'],
                rows=self.num_rows)

    def _post_draw_items(self):
        if self.blabel.labels:
            name_row = self.layouts['items_box'].row()
            name_row.prop(self.blabel.active_label, 'name')

    def _pre_draw_sidebar_top(self):
        super()._pre_draw_sidebar_top()
        if self.items:
            side_spacer = self.layouts['sidebar'].row()
            side_spacer.scale_y = 2
            side_spacer.separator()
            self.layouts['pre_sidebar_spacer'] = side_spacer
        self.num_top_sidebar_items += 1
        self.layouts['sidebar'].operator(self.operators.label_add, icon='ZOOMIN', text="")
        if self.items:
            self.num_top_sidebar_items += 1
            self.layouts['sidebar'].operator(self.operators.label_remove, icon='ZOOMOUT', text="")

    @prepost_calls
    def draw_sidebar_bottom(self):
        super().draw_sidebar_bottom()
        if len(self.items) > 1:
            self.layouts['sidebar'].operator(self.operators.label_move, icon='TRIA_UP', text="").direction = 'UP'
            self.layouts['sidebar'].operator(self.operators.label_move, icon='TRIA_DOWN', text="").direction = 'DOWN'


class BlabelItemList(BaseBlabelList):
    def __init__(self, context, layout, blabel, operators, name):
        super().__init__(context, layout, blabel, operators, name)
        self.items, self.selected = self.blabel.get_visible_items()

    def _pre_draw_items(self):
        super()._pre_draw_items()
        if self.blabel.items:
            # Draw view mode selector
            row = self.layouts['items_column'].row()
            row.menu(self.operators.view_mode, text=self.blabel.view_mode)
            row = row.split()

            row.label(self.name)
            if self.blabel.labels and len(self.blabel.labels) > 1:
                row = row.split()
                row.menu(self.operators.add_to_label_menu, text="Copy to Label")

            self.layouts['view_mode'] = row
        self.layouts['items_column'].separator()

    @prepost_calls
    def draw_items(self):
        # self.operators.label_list
        super().draw_items()

    def _post_draw_items(self):
        super()._post_draw_items()
        if self.items:
            bottom = self.layouts['items_column'].row()
            bottom.operator(self.operators.item_toggle_select, icon='PROP_ON', text='')
            self.layouts['items_bottom'] = bottom

    @prepost_calls
    def draw_item(self, item):
        super().draw_item(item)
        layouts = self.layouts

        item_row = layouts['item_row'].split(percentage=0.09, align=True)
        icon = 'PROP_OFF'
        if item == self.blabel.active_item:
            icon = 'PROP_ON'
        elif item in self.selected:
            icon = 'PROP_CON'
        item_row.operator(self.operators.item_set_index, icon=icon, text='').index = self.blabel.get_item_index(item)
        layouts['item_row'] = item_row

    def _post_draw_item(self, item):
        super()._post_draw_item(item)
        row = self.layouts['items_column'].row()
        row.scale_y = 0.5
        row.separator()

    def _pre_draw_sidebar_top(self):
        super()._pre_draw_sidebar_top()
        self.layouts['sidebar'].scale_y = 1.15
        if self.blabel.items:
            side_spacer = self.layouts['sidebar'].row()
            if self.items:
                side_spacer.scale_y = 5
            else:
                side_spacer.scale_y = 5
            side_spacer.separator()
            self.layouts['pre_sidebar_spacer'] = side_spacer

    @prepost_calls
    def draw_sidebar_top(self):
        self.num_top_sidebar_items += 1
        self.layouts['sidebar'].operator(self.operators.item_add, icon='ZOOMIN', text="")
        if self.items:
            self.num_top_sidebar_items += 2
            self.layouts['sidebar'].operator(self.operators.item_remove, icon='ZOOMOUT', text="")
            self.layouts['sidebar'].operator(self.operators.item_delete, icon='PANEL_CLOSE', text="")

    @prepost_calls
    def draw_sidebar_bottom(self):
        super().draw_sidebar_bottom()
        if len(self.items) > 1:
            self.layouts['sidebar'].operator(self.operators.item_move, icon='TRIA_UP', text="").direction = 'UP'
            self.layouts['sidebar'].operator(self.operators.item_move, icon='TRIA_DOWN', text="").direction = 'DOWN'

    def draw(self):
        '''Main draw method'''
        super().draw()



# Taken from blender ui files.  Needed when Blabels is eventually put into a UI class.
class MeshButtonsPanel():
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

    @classmethod
    def poll(cls, context):
        engine = context.scene.render.engine
        return context.mesh and (engine in cls.COMPAT_ENGINES)


class IndexProperty(bpy.types.PropertyGroup):
    index = bpy.props.IntProperty(default=-1)


class IndexCollection(bpy.types.PropertyGroup):
    indexes = bpy.props.CollectionProperty(type=IndexProperty)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = 'something'


# I wish I knew how to extend existing operators like object.shape_key_move
# So I could override those with mine, and not risk my label state machine
# becoming invalid if some other script/user calls object.shape_key_move
# instead of object.shape_key_move_to_label


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

# Shape_Key_Blabels().copy_item(14)
# Shape_Key_Blabels().select_item(138)

