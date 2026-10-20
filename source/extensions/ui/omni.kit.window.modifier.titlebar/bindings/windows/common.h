// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#pragma once

#include <Windows.h>
#include <list>
#include <string>
#include <wingdi.h>

namespace omni
{
namespace modifier
{
typedef std::string String;
typedef std::list<std::string> StringList;

class Rect;
class Point;

void fillRect(HDC dc, const RECT& rc, COLORREF color);
void drawRect(HDC dc, const RECT& rc, COLORREF color);
COLORREF mergeColor(COLORREF color1, COLORREF color2, float ratio);
std::string convertUnicodeToAnsi(const wchar_t* wstr, int len = -1);
std::wstring convertAnsiToUnicode(const char* str, int wstrlen = -1);

class Point : public POINT
{
public:
    Point(int _x = 0, int _y = 0)
    {
        x = _x;
        y = _y;
    }
    void shift(int _x, int _y);
    bool operator==(const POINT& pt) const;
    bool operator!=(const POINT& pt) const;
};

class Size : public SIZE
{
public:
    Size(int _cx = 0, int _cy = 0)
    {
        cx = _cx;
        cy = _cy;
    }

    bool operator==(const SIZE& size) const;
    bool operator!=(const SIZE& size) const;
};

class Rect : public RECT
{
public:
    Rect(int _left = 0, int _top = 0, int _right = 0, int _bottom = 0);

    void shift(int x, int y);
    Rect getCenterRect(int cx, int cy) const;
    Point getCenterPoint() const;
    Point getTopLeft() const;
    Point getBottomRight() const;
    Size getSize() const;

    void set(int _left, int _top, int _right, int _bottom);

    int width() const;
    int height() const;
    bool isPtInside(int x, int y) const;
    bool isPtInside(Point& pt) const;

    bool operator==(const RECT& rc) const;
    bool operator!=(const RECT& rc) const;
};

class Brush
{
public:
    Brush(HBRUSH handle) : m_handle(handle)
    {
    }

    Brush(int color)
    {
        m_handle = CreateSolidBrush(color);
    }

    ~Brush()
    {
        DeleteObject(m_handle);
    }

    HBRUSH getHandle()
    {
        return m_handle;
    }

    HBRUSH operator&()
    {
        return m_handle;
    }

private:
    HBRUSH m_handle;
};

class Pen
{
public:
    Pen(HPEN handle) : m_handle(handle)
    {
    }

    ~Pen()
    {
        DeleteObject(m_handle);
    }

    HPEN getHandle()
    {
        return m_handle;
    }

    HPEN operator&()
    {
        return m_handle;
    }

private:
    HPEN m_handle;
};

class ImageBase
{
public:
    ImageBase()
    {
        m_handle = nullptr;
    }
    virtual ~ImageBase()
    {
        cleanup();
    }
    virtual void cleanup();

    HGDIOBJ operator()()
    {
        return m_handle;
    }
    HGDIOBJ getHandle()
    {
        return m_handle;
    }

    bool isValid()
    {
        return !!m_handle;
    }

protected:
    HGDIOBJ m_handle;
};

class Bitmap : public ImageBase
{
public:
    Bitmap(const char* file = nullptr);
    virtual void cleanup();
    bool load(const char* file);
    void draw(HDC dc, const Rect& rc, int offset_x, int pffset_y);
    Size getSize() const
    {
        return m_size;
    }
    operator HBITMAP()
    {
        return (HBITMAP)m_handle;
    }

private:
    HBITMAP m_mask;
    Size m_size;
};

class Icon
{
public:
    Icon(const char* file);
    Icon(HICON icon = nullptr);
    virtual void cleanup();
    bool load(const char* file, int cx = 0, int cy = 0);
    void draw(HDC dc, const Rect& rc);
    void set(HICON icon)
    {
        cleanup();
        m_handle = CopyIcon(icon);
    }
    operator HICON()
    {
        return (HICON)m_handle;
    }

private:
    HICON m_handle;
};

struct LogFont
{
    LogFont()
    {
        m_name = "Arial";
        m_size = 16;
        m_color = 0x808080;
        m_bold = false;
        m_italic = false;
    }

    std::string m_name;
    int m_size;
    COLORREF m_color;
    bool m_bold;
    bool m_italic;
};

class PenSwitch
{
public:
    PenSwitch(HDC dc, HPEN pen);
    ~PenSwitch();

private:
    HDC m_dc;
    HPEN m_oldPen;
};

class Region
{
public:
    Region(const char* name) : m_name(name){};
    virtual ~Region()
    {
    }

    virtual Size draw(HDC dc, int x, int y, float scaleFactor, COLORREF colorBk, int max_x = -1) = 0;
    const std::string getName() const
    {
        return m_name;
    }

    virtual bool isText() const
    {
        return false;
    }

    static void setDefaultFont(const char* name, int size, COLORREF color);
    static const LogFont& getDefaultFont()
    {
        return m_defaultFont;
    }

protected:
    std::string m_name;
    static LogFont m_defaultFont;
};

class RegionPicture : public Region
{
public:
    RegionPicture(const char* name, const char* imgFile);
    virtual ~RegionPicture()
    {
    }

    virtual Size getSize() const
    {
        return m_bitmap.getSize();
    }
    virtual Size draw(HDC dc, int x, int y, float scaleFactor, COLORREF colorBk, int max_x = -1);

private:
    std::string m_imgFile;
    int m_scalePercents;
    COLORREF m_transparentColor;
    Bitmap m_bitmap;
};

class RegionText : public Region
{
public:
    RegionText(const char* name, const char* text);
    RegionText(const char* name, const wchar_t* text);

    virtual ~RegionText();
    void setTextA(const char* text)
    {
        m_text = text;
        m_isWide = false;
    }
    void setTextW(const wchar_t* text)
    {
        m_textW = text;
        m_isWide = true;
    }
    virtual Size draw(HDC dc, int x, int y, float scaleFactor, COLORREF colorBk, int max_x = -1);

    virtual bool isText() const
    {
        return true;
    }

    void setFont(const LogFont& font)
    {
        m_logFont = font;
        m_scaleFactor = 0.0; // Force to re-create the font
    }

private:
    std::string m_text;
    std::wstring m_textW;
    bool m_isWide;

    HFONT m_font;

    LogFont m_logFont;
    float m_scaleFactor;
};

class RegionSeparator : public Region
{
public:
    RegionSeparator(const char* name) : Region(name)
    {
    }
    virtual ~RegionSeparator()
    {
    }

    virtual Size draw(HDC dc, int x, int y, float scaleFactor, COLORREF colorBk, int max_x = -1);

    static void setColor(COLORREF color)
    {
        m_color = color;
    }

    static void setWidth(int width)
    {
        m_width = width;
    }

private:
    static COLORREF m_color;
    static int m_width;
};
} // namespace modifier
} // namespace omni
