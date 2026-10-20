# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import base64
import ctypes
import datetime
import io
import re
import tempfile
import zlib
from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

import carb
import carb.settings
import omni.client
import omni.kit.app
import omni.kit.renderer.capture
import omni.usd
import PIL.Image  # type: ignore
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.viewport.utility.camera_state import ViewportCameraState
from omni.kit.waypoint.core.external import UsdBakedPreview  # type: ignore

# HTML Export Lib
# import domonic  # type: ignore


FORMAT_EXTS = ("CSV", "XLSX", "PDF", "HTML")
SETTINGS_MARKUP_TOOL_HIDE = "/persistent/exts/omni.kit.tool.markup/tool_hide"
SETTING_MARKUP_EXPORT_LOCAL_FOLDER = "/persistent/app/markup/ExportFolder"
SETTINGS_UI_HIDE = "/app/window/hideUi"
SETTINGS_VIEWPORT_RECT = "/exts/omni.kit.markup.core/viewport_rect"


class MarkupExportObject:
    def __init__(self, markup_name: str, markup_usd) -> None:
        self._markup_name = markup_name
        self._markup_usd = markup_usd
        _markup_prim_path = self._markup_usd.get_markup_prim_path(markup_name)
        self._markup_prim = self._markup_usd._getMarkupUSD().get_prim(_markup_prim_path, False)
        self._screenshot = None

    def _get_attribute(self, attr_name: str) -> str:
        if self._markup_prim.HasAttribute(attr_name):
            attr = self._markup_prim.GetAttribute(attr_name)
            return attr.Get() or ""
        else:  # pragma: no cover
            return ""

    @property
    def author(self) -> str:
        return self._get_attribute("created_by")

    @property
    def camera_name(self) -> str:
        return self._get_attribute("camera:path")

    @property
    def comments(self) -> str:
        _comments = []
        for c in [x for x in self._markup_prim.GetChildren() if "Label" in x.GetName()]:
            t = c.GetAttribute("text").Get()
            if isinstance(t, str):
                _comments.append(t)
        return "\n".join([x.replace("\r", "\n") for x in _comments])

    @property
    def creation_date(self) -> str:
        return self._get_attribute("created")

    @property
    def frame(self) -> int:
        return 0

    @property
    def markup_name(self) -> str:
        return self._markup_name

    @property
    def notes(self) -> str:
        return self._get_attribute("comment")

    @property
    def screenshot(self) -> Optional[PIL.Image.Image]:
        return self._screenshot

    @screenshot.setter
    def screenshot(self, img: Optional[PIL.Image.Image]) -> None:
        self._screenshot = img

    @property
    def screenshot_buffer(self) -> io.BytesIO:
        img_buf = io.BytesIO()
        if isinstance(self._screenshot, PIL.Image.Image):
            self._screenshot.save(img_buf, "PNG")
        return img_buf

    @property
    def thumbnail_image(self) -> Optional[PIL.Image.Image]:
        attr = self._get_attribute("omni:baked_preview")
        if not attr or attr == "":  # pragma: no cover
            return None

        packed = base64.a85decode(attr)
        data_type = int.from_bytes(packed[0:4], "little")
        if data_type == UsdBakedPreview.PreviewType.ZIP.value:
            width = int.from_bytes(packed[4:8], "little")
            height = int.from_bytes(packed[8:12], "little")
            img_bytes = zlib.decompress(packed[12:])
            return PIL.Image.frombytes("RGBA", (width, height), img_bytes)
        else:  # pragma: no cover
            return None

    @property
    def thumbnail_buffer(self) -> Tuple[io.BytesIO, int, int]:
        PADDING = 10
        img_buf = io.BytesIO()
        img = self.thumbnail_image
        if isinstance(img, PIL.Image.Image):
            img.save(img_buf, "PNG")
            return (img_buf, img.width + PADDING, img.height + PADDING)
        else:  # pragma: no cover
            return (img_buf, -1, -1)

    @property
    def url(self) -> str:
        context = omni.usd.get_context()
        return context.get_stage_url()


class MarkupExport:
    def __init__(
        self,
        markup_instance,
        export_format_map: Dict[str, bool],
        pdf_page_size_idx: int = 0,
        pdf_page_landscape: bool = False,
    ) -> None:

        self._markup_instance = markup_instance
        self._export_format_map = export_format_map
        self._pdf_page_size_idx = pdf_page_size_idx
        self._pdf_page_landscape = pdf_page_landscape

        self._settings = carb.settings.get_settings()

        self._created = datetime.datetime.now()
        self._markup_export_objs = self._get_markup_objects(self._markup_instance)
        self._local_temp_dir: Optional[Path] = None

    @property
    def _is_remote_dest(self) -> bool:
        return self._settings.get_as_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER).lower().startswith("omniverse:")

    @property
    def export_dir(self) -> Path:
        if self._is_remote_dest:
            if self._local_temp_dir is None:
                self._local_temp_dir = Path(tempfile.mkdtemp(prefix="markup_export_"))
            return self._local_temp_dir
        export_dir = Path(self._settings.get_as_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER))
        export_dir.mkdir(exist_ok=True)
        return export_dir

    @property
    def filename(self) -> str:
        filename = self._markup_export_objs[0].url.split(r"/")[-1].split(".")[0]
        filename = re.sub(r'[\\/*?:"<>|]+', "_", filename)
        return filename

    @property
    def title(self) -> str:
        title = f'{self._markup_export_objs[0].url.split("/")[-1]} Markup Data'
        return title

    @property
    def timestamp(self) -> str:
        now = self._created
        timestamp_str = f"{now.year}-{now.month}-{now.day}_{now.hour}-{now.minute:02}-{now.second:02}"
        return timestamp_str

    @property
    def export_filepath(self) -> Path:
        return self.export_dir / f"{self.filename}_markup_data_{self.timestamp}"

    def _get_markup_objects(self, markup_instance):
        objects = [MarkupExportObject(name, markup_instance) for name in markup_instance.get_all_markup_names()]
        return objects

    async def export(self, finished_callback: Callable) -> None:
        if any([x in self._export_format_map for x in ("PDF", "HTML", "XLSX")]):
            # Attempting to store current camera state for re-setting later.
            viewport = get_active_viewport()
            camera_state = ViewportCameraState(viewport=viewport)
            cam_world_pos = camera_state.position_world
            cam_world_tgt = camera_state.target_world

            for meo in self._markup_export_objs:
                for _ in range(10):
                    await omni.kit.app.get_app().next_update_async()  # type: ignore
                await self._capture_screenshot(meo, viewport.id)
            self._markup_instance.recall_markup(None)

            # Resetting original camera position.
            camera_state.set_position_world(cam_world_pos, True)
            camera_state.set_target_world(cam_world_tgt, True)

        for format, val in self._export_format_map.items():
            if val:
                if format == FORMAT_EXTS[0]:
                    self._export_csv()
                elif format == FORMAT_EXTS[1]:
                    self._export_xlsx()
                elif format == FORMAT_EXTS[2]:
                    self._export_pdf()
                elif format == FORMAT_EXTS[3]:  # pragma: no cover
                    self._export_html()
                else:  # pragma: no cover
                    carb.log_error("No matching Markup export format found.")
        if self._is_remote_dest:
            await self._publish_to_remote()
        finished_callback()

    async def _publish_to_remote(self) -> None:
        if self._local_temp_dir is None:  # pragma: no cover
            return
        dest_root = self._settings.get_as_string(SETTING_MARKUP_EXPORT_LOCAL_FOLDER).rstrip("/")
        base_name = self.export_filepath.name
        for produced in self._local_temp_dir.glob(f"{base_name}.*"):
            dest_url = f"{dest_root}/{produced.name}"
            result = await omni.client.copy_async(str(produced), dest_url, behavior=omni.client.CopyBehavior.OVERWRITE)
            if result != omni.client.Result.OK:  # pragma: no cover
                carb.log_error(f"Failed to copy markup export to {dest_url}: {result}")
            with suppress(OSError):
                produced.unlink()
        with suppress(OSError):
            self._local_temp_dir.rmdir()
        self._local_temp_dir = None

    async def _capture_screenshot(self, markup_export_object: MarkupExportObject, viewport_id: str = "") -> None:
        stashed_settings = {}

        def restore_settings():
            for setting_path in stashed_settings:
                self._settings.set(setting_path, stashed_settings[setting_path])

        def set_bool_setting(setting_path: str, value: bool):
            stashed_settings[setting_path] = True if self._settings.get(setting_path) else False
            self._settings.set(setting_path, value)

        current_markup = self._markup_instance.get_markup(markup_export_object.markup_name)
        self._markup_instance.recall_markup(current_markup)
        # Hack to get text boxes to resize correctly on first recalled martkup.
        if markup_export_object == self._markup_export_objs[0]:
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            self._markup_instance.recall_markup(None)
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            self._markup_instance.recall_markup(current_markup)
        set_bool_setting(SETTINGS_MARKUP_TOOL_HIDE, True)
        set_bool_setting(SETTINGS_UI_HIDE, True)
        set_bool_setting(f"/persistent/app/viewport/{viewport_id}/hud/renderFPS/visible", False)
        set_bool_setting(f"/persistent/app/viewport/{viewport_id}/hud/deviceMemory/visible", False)
        set_bool_setting(f"/persistent/app/viewport/{viewport_id}/hud/hostMemory/visible", False)
        set_bool_setting(f"/persistent/app/viewport/{viewport_id}/hud/renderResolution/visible", False)
        set_bool_setting(f"/persistent/app/viewport/{viewport_id}/hud/renderProgress/visible", False)
        # OMFP-2935 - Bumping this to 40, in the hopes that things will be less blurry.
        for _ in range(40):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
        renderer_capture = omni.kit.renderer.capture.acquire_renderer_capture_interface()
        result = None

        def _on_full_window_captured(buffer, buffer_size, width, height, _format):  # pragma: no cover
            nonlocal result
            try:
                ctypes.pythonapi.PyCapsule_GetPointer.restype = ctypes.POINTER(ctypes.c_byte * buffer_size)
                ctypes.pythonapi.PyCapsule_GetPointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
                content = ctypes.pythonapi.PyCapsule_GetPointer(buffer, None)
            except Exception as e:
                carb.log_error(f"[Waypoint] Failed to get capture buffer: {e}")
                return None
            rect = carb.settings.get_settings().get(SETTINGS_VIEWPORT_RECT)
            img = PIL.Image.frombytes("RGBA", (width, height), content.contents)
            img.crop(rect)
            result = img

        renderer_capture.capture_next_frame_swapchain_callback(_on_full_window_captured)
        # waiting one frame is not enough to ensure capture from _on_full_window_captured
        # OMFP-2935 - Bumping this to 40, in the hopes that things will be less blurry.
        for _ in range(40):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
        renderer_capture.wait_async_capture()
        restore_settings()
        markup_export_object.screenshot = result

    def _export_csv(self) -> None:
        export_filepath = Path(f"{str(self.export_filepath)}.csv")
        with export_filepath.open(mode="w") as f:
            f.write(f"{self.title}\n")
            f.write("Name,Frame,Author,Creation Date,Camera Name,Comments,Notes,URL\r")
            for m in self._markup_export_objs:
                f.write(
                    f'{m.markup_name},{m.frame},{m.author},{m.creation_date},{m.camera_name},"{m.comments}","{m.notes}",{m.url}\r'
                )

    def _export_xlsx(self) -> None:
        _widths = (
            -1,
            75,
            50,
            60,
            130,
            150,
            360,
            360,
            350,
        )  # TODO: Calculate these from input item widths and set at the end
        export_filepath = Path(f"{str(self.export_filepath)}.xlsx")
        import xlsxwriter

        if xlsxwriter:
            workbook = xlsxwriter.Workbook(str(export_filepath))
            worksheet = workbook.add_worksheet("Markup Data")

            # Title
            title_format = workbook.add_format()
            title_format.set_font_size(18)
            title_format.set_bold()
            title_format.set_bottom(2)
            worksheet.write(0, 0, self.title, title_format)
            for c in range(1, 8):
                worksheet.write(0, c, "", title_format)

            # Headings
            heading_format = workbook.add_format()
            heading_format.set_bold()
            for x, hdg in enumerate(
                ("Thumbnail", "Name", "Frame", "Author", "Creation Date", "Camera Name", "Comments", "Notes", "URL")
            ):
                worksheet.write(1, x, hdg, heading_format)
                if x > 0:
                    worksheet.set_column_pixels(x, x, _widths[x])

            # Data
            data_format = workbook.add_format()
            data_format.set_align("top")
            comments_format = workbook.add_format()
            comments_format.set_align("top")
            comments_format.set_text_wrap()
            row_offset = 2
            for row, m in enumerate(self._markup_export_objs):
                thumbnail, col_0_width, row_height = m.thumbnail_buffer
                values = (
                    thumbnail,
                    m.markup_name,
                    m.frame,
                    m.author,
                    m.creation_date,
                    m.camera_name,
                    m.comments,
                    m.notes,
                    m.url,
                )
                for column, val in enumerate(values):
                    # Thumbnail
                    if column == 0:
                        try:
                            worksheet.insert_image(
                                row + row_offset, column, "", {"image_data": val, "x_offset": 5, "y_offset": 5}
                            )
                            if row + row_offset == 2:
                                worksheet.set_column_pixels(column, column, col_0_width)
                            continue
                        except:  # pragma: no cover
                            carb.log_warn("Thumbnail data for markup {m.markup_name} is corrupt or invalid.")
                            continue
                    # Comments
                    elif column in (6, 7):
                        worksheet.write(row + row_offset, column, val, comments_format)
                        continue
                    # Everything else
                    elif column + 1 < len(values):
                        worksheet.write(row + row_offset, column, val, data_format)
                    else:
                        worksheet.write_url(row + row_offset, column, val, data_format)
                worksheet.set_row_pixels(row + row_offset, row_height)
            workbook.close()

    def _export_pdf(self) -> None:
        # Deferring imports to improve startup time.
        import reportlab.lib.pagesizes as pagesizes
        from reportlab.lib.colors import blue
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.platypus import Image, PageBreak, PageTemplate, Paragraph, SimpleDocTemplate, Spacer
        from reportlab.platypus.frames import Frame

        LINK_STYLE = ParagraphStyle(name="URL", fontSize=10, leading=12, linkUnderline=True, textColor=blue)
        STYLES = getSampleStyleSheet()

        def _header(canvas: Canvas, doc: SimpleDocTemplate, content: Paragraph) -> None:
            canvas.setTitle(self.export_filepath.name)
            canvas.saveState()
            _w, h = content.wrap(doc.width, 0.60 * inch)
            content.drawOn(canvas, (0.87 * inch), doc.height + ((0.60 * inch) * 2) - h * 2)
            canvas.restoreState()

        export_filepath = Path(f"{str(self.export_filepath)}.pdf")
        page_size = (pagesizes.letter, pagesizes.A4)[self._pdf_page_size_idx]
        page_size = pagesizes.landscape(page_size) if self._pdf_page_landscape else pagesizes.portrait(page_size)
        doc = SimpleDocTemplate(
            str(export_filepath),
            pagesize=page_size,
            leftMargin=0.87 * inch,
            rightMargin=0.87 * inch,
            topMargin=0.60 * inch,
            bottomMargin=0.60 * inch,
        )

        pages: List[Union[Image, PageBreak, Paragraph, Spacer]] = []
        for m in self._markup_export_objs:
            pages.append(Paragraph(m.markup_name, STYLES.get("Heading1")))
            if m.screenshot:
                pages.append(Image(m.screenshot_buffer, *self._fit_image(page_size)))
            pages.append(Paragraph(f"Frame: {m.frame}", STYLES.get("BodyText")))
            pages.append(Paragraph(f"Author: {m.author}", STYLES.get("BodyText")))
            pages.append(Paragraph(f"Creation Date: {m.creation_date}", STYLES.get("BodyText")))
            m_comments = m.comments.replace("\n", " | ")
            pages.append(Paragraph(f"Comments: {m_comments}", STYLES.get("BodyText")))
            pages.append(Paragraph(f"Notes: {m.notes}", STYLES.get("BodyText")))
            pages.append(Spacer(0, 5))
            with suppress(AttributeError):  # OM-75937 - Sometimes this line isn't valid for reportlib (?)
                pages.append(Paragraph(f"<link href={m.url}>{m.url}</link>", LINK_STYLE))
            pages.append(PageBreak())

        frame = Frame(0.87 * inch, 0.60 * inch, doc.width, doc.height, id="normal")
        header_content = Paragraph(self.title, STYLES.get("Normal"))
        template = PageTemplate(id="markup_export", frames=frame, onPage=partial(_header, content=header_content))
        doc.addPageTemplates([template])
        doc.build(pages)

    def _export_html(self) -> None:  # pragma: no cover
        # export_filepath = Path(f"{str(self.export_filepath)}.html")
        raise NotImplementedError

    def _fit_image(self, page_size: Tuple[float, float]) -> Tuple[float, float]:
        if self._pdf_page_landscape:
            h = page_size[-1] * 0.50
            w = h * 1.778  # 16:9
            return (w, h)
        w = page_size[0] * 0.666
        h = w * 0.563  # 9:16
        return (w, h)
