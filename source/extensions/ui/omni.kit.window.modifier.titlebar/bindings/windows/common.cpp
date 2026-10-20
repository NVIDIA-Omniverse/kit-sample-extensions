// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "../debug.h"
// #include "../WindowModifier.h"

#if defined(_WIN32)

#    include "common.h"
#    include <windowsx.h>

namespace omni
{
namespace modifier
{

void Point::shift(int _x, int _y)
{
    x += _x;
    y += _y;
}

bool Point::operator==(const POINT& pt) const
{
    return x == pt.x && y == pt.y;
}

bool Point::operator!=(const POINT& pt) const
{
    return x != pt.x || y != pt.y;
}

bool Size::operator==(const SIZE& size) const
{
    return cx == size.cx && cy == size.cy;
}

bool Size::operator!=(const SIZE& size) const
{
    return cx != size.cx || cy != size.cy;
}

Rect::Rect(int _left, int _top, int _right, int _bottom)
{
    set(_left, _top, _right, _bottom);
}

void Rect::set(int _left, int _top, int _right, int _bottom)
{
    left = _left;
    right = _top;
    top = _right;
    bottom = _bottom;
}

void Rect::shift(int x, int y)
{
    left += x;
    right += x;
    top += y;
    bottom += y;
}

Rect Rect::getCenterRect(int cx, int cy) const
{
    Rect rc;
    rc.left = left + (width() - cx) / 2;
    rc.right = rc.left + cx;
    rc.top = top + (height() - cy) / 2;
    rc.bottom = rc.top + cy;

    return rc;
}

Point Rect::getCenterPoint() const
{
    Point center;
    center.x = (left + right) / 2;
    center.y = (top + bottom) / 2;

    return center;
}

Point Rect::getTopLeft() const
{
    Point pt;
    pt.x = left;
    pt.y = top;

    return pt;
}

Point Rect::getBottomRight() const
{
    Point pt;
    pt.x = right;
    pt.y = bottom;

    return pt;
}

Size Rect::getSize() const
{
    return Size(width(), height());
}

int Rect::width() const
{
    return right - left;
}

int Rect::height() const
{
    return bottom - top;
}

bool Rect::isPtInside(int x, int y) const
{
    if (x >= left && x < right && y >= top && y < bottom)
        return true;

    return false;
}

bool Rect::isPtInside(Point& pt) const
{
    return isPtInside(pt.x, pt.y);
}

bool Rect::operator==(const RECT& rc) const
{
    return (left == rc.left) && (right == rc.right) && (top == rc.top) && (bottom == rc.bottom);
}

bool Rect::operator!=(const RECT& rc) const
{
    return (left != rc.left) || (right != rc.right) || (top != rc.top) || (bottom != rc.bottom);
}

void ImageBase::cleanup()
{
    if (m_handle)
    {
        DeleteObject(m_handle);
        m_handle = nullptr;
    }
}

Bitmap::Bitmap(const char* file)
{
    m_mask = nullptr;

    if (file)
        load(file);
}

void Bitmap::cleanup()
{
    if (m_mask)
    {
        DeleteObject(m_mask);
        m_mask = nullptr;
    }
    ImageBase::cleanup();
}

bool Bitmap::load(const char* file)
{
    cleanup();

    m_handle = (HBITMAP)LoadImageA(nullptr, file, IMAGE_BITMAP, 0, 0, LR_LOADFROMFILE);
    if (!m_handle)
    {
        CARB_LOG_ERROR("load %s failed! GetLastError: 0x%08x\n", file, GetLastError());
        return false;
    }

    BITMAP bm;
    GetObject(m_handle, sizeof(BITMAP), &bm);
    m_size.cx = bm.bmWidth;
    m_size.cy = bm.bmHeight;
    DBG_PRINT("load %s sucessfully, size:%d, %d\n", file, m_size.cx, m_size.cy);

    // Create the mask bitmap
    m_mask = CreateBitmap(bm.bmWidth, bm.bmHeight, 1, 1, NULL);

    // Prepare 2 HDC to make the mask
    HDC dcSrc, dcDst;
    dcSrc = CreateCompatibleDC(NULL);
    dcDst = CreateCompatibleDC(NULL);

    // Load the 2 bitmaps into the 2 HDC
    HBITMAP bmSaveSrc = SelectBitmap(dcSrc, m_handle);
    COLORREF transparentColor = GetPixel(dcSrc, 0, 0);
    HBITMAP bmSaveDst = SelectBitmap(dcDst, m_mask);

    // Change the background to transparent color
    COLORREF clrSaveBg = SetBkColor(dcSrc, transparentColor);

    // Sets up the mask bitmap.
    BitBlt(dcDst, 0, 0, bm.bmWidth, bm.bmHeight, dcSrc, 0, 0, SRCCOPY);
    COLORREF clrSaveFg = SetTextColor(dcSrc, RGB(255, 255, 255));
    SetBkColor(dcSrc, RGB(0, 0, 0));

    BitBlt(dcSrc, 0, 0, bm.bmWidth, bm.bmHeight, dcDst, 0, 0, SRCAND);

    // Cleanup
    SetTextColor(dcSrc, clrSaveFg);
    SetBkColor(dcSrc, clrSaveBg);

    SelectBitmap(dcSrc, bmSaveSrc);
    SelectBitmap(dcDst, bmSaveDst);

    DeleteDC(dcSrc);
    DeleteDC(dcDst);
    return true;
}

void Bitmap::draw(HDC dc, const Rect& rc, int offset_x, int offset_y)
{
    HDC dcMsk = CreateCompatibleDC(NULL);
    HBITMAP saveMsk = SelectBitmap(dcMsk, m_mask);
    BitBlt(dc, rc.left, rc.top, rc.width(), rc.height(), dcMsk, offset_x, offset_y, SRCAND);

    HDC dcBmp = CreateCompatibleDC(dc);
    HBITMAP saveBmp = SelectBitmap(dcBmp, m_handle);
    BitBlt(dc, rc.left, rc.top, rc.width(), rc.height(), dcMsk, offset_x, offset_y, SRCAND);
    BitBlt(dc, rc.left, rc.top, rc.width(), rc.height(), dcBmp, offset_x, offset_y, SRCPAINT);

    SelectBitmap(dcMsk, saveMsk);
    SelectBitmap(dcBmp, saveBmp);

    DeleteDC(dcMsk);
    DeleteDC(dcBmp);
}

Icon::Icon(const char* file)
{
    if (file)
    {
        load(file);
    }
}

Icon::Icon(HICON icon)
{
    if (icon)
    {
        set(icon);
    }
}

void Icon::cleanup()
{
    if (m_handle)
    {
        DestroyIcon((HICON)m_handle);
        m_handle = nullptr;
    }
}

bool Icon::load(const char* file, int cx, int cy)
{
    m_handle = (HICON)LoadImageA(nullptr, file, IMAGE_ICON, cx, cy, LR_LOADFROMFILE);
    if (!m_handle)
    {
        CARB_LOG_ERROR("load %s failed! GetLastError:0x%08x", file, GetLastError());
        return false;
    }

    return true;
}

void Icon::draw(HDC dc, const Rect& rc)
{
    if (m_handle)
    {
        DrawIconEx(dc, rc.left, rc.top, *this, rc.width(), rc.height(), 0, nullptr, DI_NORMAL);
    }
}

PenSwitch::PenSwitch(HDC dc, HPEN pen)
{
    m_dc = dc;
    m_oldPen = SelectPen(dc, pen);
}

PenSwitch::~PenSwitch()
{
    SelectPen(m_dc, m_oldPen);
}

LogFont Region::m_defaultFont;
void Region::setDefaultFont(const char* name, int size, COLORREF color)
{
    m_defaultFont.m_name = name;
    m_defaultFont.m_size = size;
    m_defaultFont.m_color = color;
}

RegionPicture::RegionPicture(const char* name, const char* imgFile) : Region(name)
{
    m_imgFile = imgFile;
    m_scalePercents = 0;
}

Size RegionPicture::draw(HDC dc, int x, int y, float scaleFactor, COLORREF colorBk, int max_x)
{
    (void)colorBk;
    Size size;

    int scalePercents = (int)round(100 * scaleFactor);
    if (scalePercents <= 100)
        scalePercents = 100;
    else if (scalePercents <= 125)
        scalePercents = 125;
    else if (scalePercents <= 150)
        scalePercents = 150;
    else if (scalePercents <= 200)
        scalePercents = 200;
    else if (scalePercents <= 250)
        scalePercents = 250;
    else if (scalePercents <= 300)
        scalePercents = 300;
    else
        scalePercents = 350;

    if (scalePercents != m_scalePercents)
    {
        char bufFile[MAX_PATH];
        sprintf_s<MAX_PATH>(bufFile, m_imgFile.c_str(), scalePercents);
        if (!m_bitmap.load(bufFile))
            return size;
        m_scalePercents = scalePercents;
    }

    size = m_bitmap.getSize();

    Rect rc;
    rc.left = x;
    rc.top = y - size.cy / 2;
    rc.right = x + size.cx;
    rc.bottom = rc.top + size.cy;

    m_bitmap.draw(dc, rc, 0, 0);

    return size;
}

RegionText::RegionText(const char* name, const char* text)
    : Region(name), m_text(text), m_font(NULL), m_logFont(m_defaultFont), m_isWide(false)
{
    m_scaleFactor = 0.0f;
    m_font = NULL;
}

RegionText::RegionText(const char* name, const wchar_t* text)
    : Region(name), m_textW(text), m_font(NULL), m_logFont(m_defaultFont), m_isWide(true)
{
    m_scaleFactor = 0.0f;
    m_font = NULL;
}
RegionText::~RegionText()
{
    if (m_font)
        DeleteObject(m_font);
}

Size RegionText::draw(HDC dc, int x, int y, float scaleFactor, COLORREF colorBk, int max_x)
{
    if (x >= max_x)
    {
        CARB_LOG_ERROR("No space for RegionText\n");
        return Size(0, 0);
    }

    COLORREF oldTxtColor = SetTextColor(dc, m_logFont.m_color);
    COLORREF oldBkCoor = SetBkColor(dc, colorBk);

    int fontSize = (int)round(m_logFont.m_size * scaleFactor);
    if (!m_font || abs(m_scaleFactor - scaleFactor) > .01f)
    {
        if (m_font)
            DeleteObject(m_font);

        int weight = FW_NORMAL;
        if (m_logFont.m_bold)
            weight = FW_BOLD;

        DWORD italic = FALSE;
        if (m_logFont.m_italic)
            italic = TRUE;

        m_font = CreateFontA(fontSize, // nHeight
                             0, // nWidth
                             0, // nEscapement
                             0, // nOrientation
                             weight, // nWeight
                             italic, // bItalic
                             FALSE, // bUnderline
                             0, // cStrikeOut
                             ANSI_CHARSET, // nCharSet
                             OUT_DEFAULT_PRECIS, // nOutPrecision
                             CLIP_DEFAULT_PRECIS, // nClipPrecision
                             DEFAULT_QUALITY, // nQuality
                             DEFAULT_PITCH | FF_SWISS, // nPitchAndFamily
                             m_logFont.m_name.c_str()); // lpszFacename
        m_scaleFactor = scaleFactor;
    }
    HFONT oldFont = SelectFont(dc, m_font);

    Rect rcText;
    DWORD drawFlags = DT_SINGLELINE;
    if (m_isWide)
    {
        DrawTextW(dc, m_textW.c_str(), (int)m_textW.length(), &rcText, drawFlags | DT_CALCRECT);
        rcText.shift(x, y - rcText.height() / 2);
        if (max_x > 0 && max_x < rcText.right)
            rcText.right = max_x;
        DrawTextW(dc, m_textW.c_str(), (int)m_textW.length(), &rcText, drawFlags | DT_END_ELLIPSIS);
    }
    else
    {
        DrawTextA(dc, m_text.c_str(), (int)m_text.length(), &rcText, drawFlags | DT_CALCRECT);
        rcText.shift(x, y - rcText.height() / 2);
        if (max_x > 0 && max_x < rcText.right)
            rcText.right = max_x;
        DrawTextA(dc, m_text.c_str(), (int)m_text.length(), &rcText, drawFlags | DT_END_ELLIPSIS);
    }

    SetTextColor(dc, oldTxtColor);
    SetBkColor(dc, oldBkCoor);
    SelectFont(dc, oldFont);

    return rcText.getSize();
}

Size RegionSeparator::draw(HDC dc, int x, int y, float scaleFactor, COLORREF colorBk, int max_x)
{
    // spearator is m_width x 16 @ 100%
    int width = (int)std::ceil(m_width * scaleFactor);
    int height = (int)std::ceil(16.0 * scaleFactor);

    int y1 = y - height / 2;
    int y2 = y1 + height;
    Pen sepPen = CreatePen(PS_SOLID, 1, m_color);
    HPEN oldPen = SelectPen(dc, &sepPen);

    if (width + x >= max_x)
        width = max_x - x;

    for (int i = 0; i < width; ++i)
    {
        MoveToEx(dc, x + i, y1, NULL);
        LineTo(dc, x + i, y2);
    }

    return Size(width, height);
}

COLORREF RegionSeparator::m_color = RGB(118, 185, 0);
int RegionSeparator::m_width = 1;

void fillRect(HDC dc, const RECT& rc, COLORREF color)
{
    // Draw the background
    Brush brush = ::CreateSolidBrush(color);
    HBRUSH oldBrush = (HBRUSH)::SelectObject(dc, &brush);
    ::FillRect(dc, &rc, &brush);
    ::SelectObject(dc, oldBrush);
}

void drawRect(HDC dc, const RECT& rc, COLORREF color)
{
    Pen borderPen = CreatePen(PS_SOLID, 1, color);
    HPEN oldPen = SelectPen(dc, &borderPen);
    MoveToEx(dc, rc.left, rc.top, nullptr);
    LineTo(dc, rc.left, rc.bottom);
    LineTo(dc, rc.right, rc.bottom);
    LineTo(dc, rc.right, rc.top);
    LineTo(dc, rc.left, rc.top);
    SelectObject(dc, oldPen);
}

COLORREF mergeColor(COLORREF color1, COLORREF color2, float ratio)
{
    int r1 = color1 & 0xff;
    int g1 = (color1 >> 8) & 0xff;
    int b1 = (color1 >> 16) & 0xff;

    int r2 = color2 & 0xff;
    int g2 = (color2 >> 8) & 0xff;
    int b2 = (color2 >> 16) & 0xff;

    int r = (int)(r1 * ratio + r2 * (1.0f - ratio));
    int g = (int)(g1 * ratio + g2 * (1.0f - ratio));
    int b = (int)(b1 * ratio + b2 * (1.0f - ratio));

    return RGB(r, g, b);
}

std::wstring convertAnsiToUnicode(const char* str, int len)
{
    // Convert a ANSI string to an Unicode string

    std::wstring result = L"Unknown";
    if (len == -1)
    {
        len = (int)strlen(str);
    }

    int needed = MultiByteToWideChar(CP_UTF8, 0, str, len, nullptr, 0);
    if (needed > 0)
    {
        result.resize(needed + 10);
        MultiByteToWideChar(CP_UTF8, 0, str, len, &result[0], (int)result.size());
    }

    return result;
}

std::string convertUnicodeToAnsi(const wchar_t* wstr, int wstrLen)
{
    // Convert a Unicode string to an ASCII string

    std::string result = "Unknown";
    if (wstrLen < 0)
    {
        wstrLen = (int)wcslen(wstr);
    }
    int needed = WideCharToMultiByte(CP_ACP, 0, wstr, wstrLen, nullptr, 0, NULL, NULL);
    result.reserve(needed + 10);
    WideCharToMultiByte(CP_ACP, 0, wstr, wstrLen, &result[0], (int)result.size(), NULL, NULL);
    return result;
}

} // namespace modifier
} // namespace omni

#endif // _WIN32
