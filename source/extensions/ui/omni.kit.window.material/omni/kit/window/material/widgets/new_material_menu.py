import omni.usd
from omni import ui
from omni.kit.material.library import get_material_list
from omni.kit.menu.utils import MenuItemDescription
from pxr import Tf, Usd


class NewMaterialMenu:
    """
    Menu for new materials.
    """

    __INSTANCE__ = None

    @staticmethod
    def get_instance():
        if NewMaterialMenu.__INSTANCE__ is None:
            NewMaterialMenu.__INSTANCE__ = NewMaterialMenu()
        return NewMaterialMenu.__INSTANCE__

    @staticmethod
    def show():
        """
        Show new materials menu.
        """
        instance = NewMaterialMenu.get_instance()
        instance._show()

    @staticmethod
    def set_on_material_created_fn(on_material_created_fn: callable):
        self = NewMaterialMenu.get_instance()
        self._on_material_created_fn = on_material_created_fn

    def __init__(self):
        self._menu = None
        self._on_material_created_fn = None
        self.__stage_notice = None

        self.__INSTANCE__ = self

    def __del__(self):
        self.__stage_notice = None

    def _show(self):
        if self._menu is None:
            sub_menu = []
            sub_menus = {}

            for mat in get_material_list():
                if mat[0] == "GROUP":
                    sub_menu.append(MenuItemDescription(header=mat[1]))
                elif mat[3]:
                    if not mat[3] in sub_menus:
                        sub_menus[mat[3]] = []
                        sub_menu.append(MenuItemDescription(name=mat[3], sub_menu=sub_menus[mat[3]]))
                    sub_menus[mat[3]].append(
                        MenuItemDescription(
                            name=mat[0], onclick_fn=lambda n=mat[0], f=mat[1]: self._create_material(n, f)
                        )
                    )
                else:
                    sub_menu.append(
                        MenuItemDescription(
                            name=mat[0], onclick_fn=lambda n=mat[0], f=mat[1]: self._create_material(n, f)
                        )
                    )

            self._menu = ui.Menu(
                "Material Browser Window Stage Materials ConText Menu", style={"Separator": {"color": 0xFF6F6F6F}}
            )
            with self._menu:
                for desc in sub_menu:
                    if desc.sub_menu:
                        sub_material_menu = ui.Menu(desc.name)
                        with sub_material_menu:
                            for sub_desc in desc.sub_menu:
                                ui.MenuItem(sub_desc.name, triggered_fn=sub_desc.onclick_fn)
                    elif desc.header:
                        ui.Separator(desc.header)
                    else:
                        ui.MenuItem(desc.name, triggered_fn=desc.onclick_fn)
        self._menu.show()

    def _create_material(self, name, create_fn):

        if self._on_material_created_fn is not None:
            if name == "Custom MDL Material":
                self._new_material_prefix = f"/World/Looks/"
            elif name == "USD Preview Surface":
                self._new_material_prefix = f"/World/Looks/PreviewSurface"
            elif name == "USD Preview Surface Texture":
                self._new_material_prefix = f"/World/Looks/PreviewSurfaceTexture"
            else:
                self._new_material_prefix = f"/World/Looks/{name}"

            if self.__stage_notice is not None:
                self.__stage_notice = None
            usd_context = omni.usd.get_context("")
            stage = usd_context.get_stage()
            if stage:
                self.__stage_notice = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, stage)

        from omni.kit.actions.core import get_action_registry

        action_registry = get_action_registry()
        action = action_registry.get_action("omni.kit.material.library", "create_material_and_assign")
        action.execute(create_fn)

    def _on_objects_changed(self, notice, sender):
        for p in notice.GetResyncedPaths():
            if p.pathString.startswith(self._new_material_prefix):
                if self._on_material_created_fn is not None:
                    self._on_material_created_fn(p)
                    self.__stage_notice = None
