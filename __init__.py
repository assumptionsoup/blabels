bl_info = {
    "name": "Advanced Panels",
    "author": "Jordan Hueckstaedt",
    "version": (1, 2),
    "blender": (2, 63, 0),
    "location": "Properties > Shape Keys / Vertex Groups",
    "warning": "", # used for warning icon and text in addons panel
    "description": "Allows the user to group shape keys into labels.\
	Also adds new functions for manipulating shape keys.",
    "wiki_url": "",
	"tracker_url": "",
	"support": "TESTING",
    "category": "Rigging"
}

# To support reload properly, try to access a package var, if it's there, reload everything
if "bpy" in locals():
	import imp
	imp.reload(advanced_labels)
	imp.reload(advanced_shape_key_panel)
	imp.reload(advanced_vertex_group_panel)
else:
	import advanced_labels
	import advanced_shape_key_panel
	import advanced_vertex_group_panel

import bpy

def register():
	# Register collections
	bpy.utils.register_class(advanced_labels.IndexProperty)
	bpy.utils.register_class(advanced_labels.IndexCollection)

	# Register panel(s)
	advanced_shape_key_panel.register()
	advanced_vertex_group_panel.register()

def unregister():
	advanced_shape_key_panel.unregister()
	advanced_vertex_group_panel.unregister()
	
	bpy.utils.unregister_class(advanced_labels.IndexProperty)
	bpy.utils.unregister_class(advanced_labels.IndexCollection)


if __name__ == "__main__":
    register()
