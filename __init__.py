bl_info = {
    "name": "B-Labels",
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
	imp.reload(blabel)
	imp.reload(shape_key_panel)
	imp.reload(vertex_group_panel)
else:
	from . import blabels
	from . import shape_key_panel
	from . import vertex_group_panel

import bpy

def register():
	# Register collections
	bpy.utils.register_class(blabels.IndexProperty)
	bpy.utils.register_class(blabels.IndexCollection)

	# Register panel(s)
	shape_key_panel.register()
	vertex_group_panel.register()

	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)

	# IndexProperty and IndexCollection are part of this module, so they
	# are already unregistered in unregister_module.  They only needed to
	# be registered explicitly, because they needed to be registered before
	# specific panels.

	vertex_group_panel.unregister()
	shape_key_panel.unregister()


if __name__ == "__main__":
    register()
