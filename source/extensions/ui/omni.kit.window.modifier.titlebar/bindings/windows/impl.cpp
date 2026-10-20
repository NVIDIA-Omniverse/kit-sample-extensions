// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "../WindowModifier.h"

// #define LOCAL_DEBUG

#include "../debug.h"

#if defined(_WIN32)

#    include "common.h"

#    include <assert.h>
#    include <cmath>
#    include <cwchar>
#    include <fstream>
#    include <iostream>
#    include <map>
#    include <shlwapi.h>
#    include <stdarg.h>
#    include <string>
#    include <unordered_map>
#    include <vector>
#    include <windowsx.h>
#    include <winuser.h>

namespace omni
{
namespace modifier
{

#    define HOVER_TIMER_ID 0x7307
#    define HOVER_TIMER_UELAPSE 100


class WindowPosition
{
private:
    WindowState m_state;
    Point m_coordinate;
    Size m_size;

    bool m_isStateChanged;
    bool m_isSizeChanged;
    bool m_isCoordinateChanged;

public:
    WindowPosition()
    {
        clearChangeFlag();
        m_state = eInvalid;
    }
    WindowState getState()
    {
        return m_state;
    }

    void setState(WindowState state)
    {
        if (m_state != state)
        {
            DBG_PRINT("Window state: %d\n", state);
            m_state = state;
            m_isStateChanged = true;
        }
    }

    const Point& getCoordinate()
    {
        return m_coordinate;
    }

    void setCoordinate(const Point& coordinate)
    {
        if (m_coordinate != coordinate)
        {
            m_coordinate = coordinate;
            m_isCoordinateChanged = true;
        }
    }

    const Size& getSize()
    {
        return m_size;
    }

    void setSize(const Size& size)
    {
        if (m_size != size)
        {
            m_size = size;
            m_isSizeChanged = true;
        }
    }

    bool isChanged()
    {
        return (m_isStateChanged || m_isCoordinateChanged || m_isSizeChanged);
    }

    bool isSizeChanged()
    {
        return m_isSizeChanged;
    }

    void clearChangeFlag()
    {
        m_isStateChanged = false;
        m_isSizeChanged = false;
        m_isCoordinateChanged = false;
    }
};

class ReentryBlocker
{
public:
    ReentryBlocker(bool& blockFlag) : m_blockFlag(blockFlag)
    {
        m_blockFlag = true;
    }

    ~ReentryBlocker()
    {
        m_blockFlag = false;
    }

private:
    bool& m_blockFlag;
};

class Impl : public WindowModifier
{
private:
    // main APP icon
    Icon m_appIcon;

    // The Regions added to show in the title bar
    typedef std::list<Region*> Regions;
    Regions m_regions;

    // The color scheme, include the following colors:
    // "caption" : the caption background color
    // "border" : the border color around the window
    // "min" : the hovered background color of the min button
    // "max" : the hovered background color of the max button
    // "close" : the hovered background color of the close button
    typedef std::map<String, COLORREF> Colors;
    Colors m_colors;

    // For region named "title" and content = "auto", it means auto-draw the title
    // : Find the orinal title, draw its substr of file-name.
    RegionText* m_regionTitle;
    // Show full file name in the title
    bool m_showFileFullPath;
    // If respond on mouse up. (else respond on mouse down when click the title buttons: min, max, close)
    bool m_respondOnMouseUp;
    // If change the window region
    bool m_changeWindowRegion;

    // The following is variables to save information after start()

    WNDPROC m_oldProc;
    HWND m_wnd;

    // Original border width of the window.
    int m_orgBorderWidth;
    // The height of the caption bar. = original cap height - border width
    int m_captionHeight;
    // The area that can be customed, it follows the app icon
    int m_regionStart_x;
    // The border width that we paint.
    int m_borderWidth;

    // Current window position/state
    WindowPosition m_windowPos;

    // Rects that related to our original window (top-left), not the Rgn.
    Rect m_rcCaption, m_rcAppIcon, m_rcButtons, m_rcMin, m_rcMax, m_rcClose;

    // Last NCHITTEST result
    LRESULT m_lastHit;
    // Current button that mouse-down on
    LRESULT m_curClicked;
    // Is any button hovered
    bool m_isHovered;
    // In some process that need no hook any message
    bool m_reentryLocked;

    // The singleton
    static Impl* m_singleton;

    // Is application is shutting down
    bool m_appShutdown;

    // Scale factor of DPI
    float m_dpiScaleFactor;

    // Current opened file path name
    std::wstring m_filePathName;

private:
    Impl()
    {
        // Default value for border width
        m_borderWidth = 2;

        // Default value for colors
        m_colors["caption"] = RGB(224, 224, 224);
        m_colors["client"] = RGB(224, 224, 224);
        m_colors["border"] = RGB(175, 175, 175);
        m_colors["min"] = RGB(188, 188, 188);
        m_colors["max"] = RGB(188, 188, 188);
        m_colors["close"] = RGB(232, 17, 35);
        m_colors["button"] = RGB(56, 56, 56);

        // Default not auto-draw the title
        m_regionTitle = nullptr;
        m_showFileFullPath = true;
        m_respondOnMouseUp = false;
        m_changeWindowRegion = false;

        m_oldProc = nullptr;
        m_wnd = nullptr;

        m_lastHit = HTCAPTION;
        m_curClicked = HTNOWHERE;
        m_isHovered = false;
        m_reentryLocked = false;
        m_orgBorderWidth = 3;

        m_singleton = this;
        m_dpiScaleFactor = 1.0;
        m_appShutdown = false;
    }

    virtual ~Impl()
    {
        stop();

        m_singleton = nullptr;
        for (auto iter = m_regions.begin(); iter != m_regions.end(); ++iter)
        {
            delete *iter;
        }
    }

public:
    static Impl* create()
    {
        if (m_singleton)
            return m_singleton;
        return new Impl();
    }

public:
    // Interfaces

    bool start(void* hwnd);
    void stop();

    // Static interfaces, can be called before start()
    virtual void setBorderWidth(int width);
    virtual void setColor(const char* category, int color);
    virtual void setSeparator(int color, int width);
    virtual void setDefaultFont(const char* fontName, int fontSize, int fontColor);

    virtual void setShowFullPath(bool value);
    virtual void setRespondOnMouseUp(bool value);
    virtual void setChangeWindowRegion(bool value);
    virtual const char* addRegion(const char* name, const char* type, const char* context, const char* attributes);
    virtual void delRegion(const char* regName);
    virtual void delAllRegions(void);

private:
    float getDpiScaleFactor();
    Region* createProperRegion(const char* name, const char* type);

    void redrawWindow()
    {
        if (m_wnd)
        {
            SetWindowPos(m_wnd, 0, 0, 0, 0, 0, SWP_DRAWFRAME | SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOZORDER);
        }
    }

    static LRESULT CALLBACK windowProc(HWND hwnd, // handle to window
                                       UINT uMsg, // message identifier
                                       WPARAM wParam, // first message parameter
                                       LPARAM lParam // second message parameter
    )
    {
        CARB_ASSERT(m_singleton);
        return m_singleton->processMessage(hwnd, uMsg, wParam, lParam);
    }

    LRESULT processMessage(HWND hwnd, // handle to window
                           UINT uMsg, // message identifier
                           WPARAM wParam, // first message parameter
                           LPARAM lParam // second message parameter
    );

    LRESULT draw();
    LRESULT processNcHitTest(WPARAM wParam, LPARAM lParam);
    LRESULT processNcLButtonDown(WPARAM wParam, LPARAM lParam);
    LRESULT processNcLButtonUp(WPARAM wParam, LPARAM lParam);
    LRESULT processTimer(WPARAM wParam, LPARAM lParam);

    LRESULT respondButton(UINT uMsg, WPARAM wParam, LPARAM lParam);

    void convertScreenToWindow(Point& pt)
    {
        Point coordinate = m_windowPos.getCoordinate();
        pt.shift(-coordinate.x, -coordinate.y);
    }

    // File name should always be unicode, but we still keep this ansi one.
    void updateFileName(const wchar_t* title = nullptr)
    {
        if (!m_regionTitle)
            return;

        if (title)
        {
            m_filePathName = title;
        }
        else
        {
            title = m_filePathName.c_str();
        }

        const wchar_t* file = wcsstr(title, L" - ");
        if (file)
        {
            file += 3;

            if (!m_showFileFullPath)
            {
                const wchar_t* file_name = wcsrchr(file, L'\\');
                if (file_name)
                {
                    file = file_name + 1;
                }
                else if (file_name = wcsrchr(file, L'/'))
                {
                    file = file_name + 1;
                }
            }

            m_regionTitle->setTextW(file);
        }
        else
        {
            m_regionTitle->setTextW(L"New Stage");
        }
    }

    void setHovered()
    {
        if (!m_isHovered)
        {
            m_isHovered = true;
            SetTimer(m_wnd, HOVER_TIMER_ID, HOVER_TIMER_UELAPSE, nullptr);
        }
    }

    void cleanHovered()
    {
        if (m_isHovered)
        {
            KillTimer(m_wnd, HOVER_TIMER_ID);
            m_isHovered = false;
        }
    }

    void initWindowRects();
    void refreshWindowRects();
};

Impl* Impl::m_singleton = nullptr;


bool Impl::start(void* hwnd)
{
    if (m_oldProc)
    {
        CARB_LOG_ERROR("Title Bar Modifier already started!\n");
        return true;
    }

    m_wnd = reinterpret_cast<HWND>(hwnd);

    // Get the window icon
    HICON icon = reinterpret_cast<HICON>(::SendMessageW(m_wnd, WM_GETICON, ICON_SMALL, 0));
    if (icon == 0)
    {
        // Alternative method. Get from the window class
        icon = reinterpret_cast<HICON>(::GetClassLongPtrW(m_wnd, GCLP_HICONSM));
    }
    if (icon != 0)
    {
        m_appIcon.set(icon);
    }

    m_dpiScaleFactor = getDpiScaleFactor();
    initWindowRects();

    m_oldProc = (WNDPROC)SetWindowLongPtr(m_wnd, GWLP_WNDPROC, (LONG_PTR)windowProc);

    // draw();
    // updateFileName();
    redrawWindow();

    DBG_PRINT("Titlebar modifier started!\n");

    return true;
}

void Impl::stop(void)
{
    DBG_PRINT("Titlebar modifier stoped!\n");
    ReentryBlocker blocker(m_reentryLocked);

    if (m_oldProc)
    {
        SetWindowLongPtr(m_wnd, GWLP_WNDPROC, (LONG_PTR)m_oldProc);
        m_oldProc = nullptr;
    }

    if (m_wnd)
    {
        if (m_changeWindowRegion)
            SetWindowRgn(m_wnd, NULL, true);
        else if (!m_appShutdown)
            redrawWindow();

        m_wnd = NULL;
    }

    m_appIcon.cleanup();
}

void Impl::setBorderWidth(int width)
{
    m_borderWidth = width;
    if (m_wnd)
    {
        initWindowRects();
    }
}

void Impl::setColor(const char* category, int color)
{
    m_colors[category] = (COLORREF)color;
    redrawWindow();
}

void Impl::setDefaultFont(const char* fontName, int fontSize, int fontColor)
{
    Region::setDefaultFont(fontName, fontSize, fontColor);
}

void Impl::setSeparator(int color, int width)
{
    RegionSeparator::setColor((COLORREF)color);
    RegionSeparator::setWidth(width);
}

void Impl::setShowFullPath(bool value)
{
    m_showFileFullPath = value;
    updateFileName();
    redrawWindow();
}

void Impl::setRespondOnMouseUp(bool value)
{
    m_respondOnMouseUp = value;
}

void Impl::setChangeWindowRegion(bool value)
{
    if ((m_changeWindowRegion && value) || !(m_changeWindowRegion || value))
        return;

    m_changeWindowRegion = value;
    if (m_wnd)
    {
        refreshWindowRects();
    }
}

void trimString(String& str)
{
    size_t start = 0, end = str.length();
    const char* delims = "\t \r\n";
    while (strchr(delims, str[start]) != NULL)
        start++;
    while (strchr(delims, str[end - 1]) != NULL)
        end--;
    str = str.substr(start, end - start);
}

const char* Impl::addRegion(const char* name, const char* type, const char* context, const char* attributes)
{
    Region* region = nullptr;

    DBG_PRINT("Add region, name = '%s', type = '%s', context = '%s', attributes = %s\n", name, type,
              context ? context : "NULL", attributes ? attributes : "NULL");

    if (!context)
    {
        context = "";
    }

    if (!type || _stricmp("text", type) == 0)
    {
        region = new RegionText(name, context);
    }
    else if (_stricmp("separator", type) == 0)
    {
        region = new RegionSeparator(name);
    }
    else if (_stricmp("image", type) == 0)
    {
        region = new RegionPicture(name, context);
    }
    else if (_stricmp("file", type) == 0)
    {
        m_regionTitle = new RegionText(name, context);
        region = m_regionTitle;
        // updateFileName();
    }
    else
    {
        CARB_LOG_ERROR("Unknown token in title format string: %s", type);
        return nullptr;
    }

    if (region && region->isText() && attributes)
    {
        String attr_str(attributes);
        StringList tokens;

        size_t start = 0, len = 0;
        while (start + len < attr_str.length())
        {
            while (attr_str[start + len] != ',' && start + len < attr_str.length())
                len++;
            tokens.push_back(attr_str.substr(start, len));
            start += len + 1;
            len = 0;
        }

        StringList::iterator it;
        LogFont font(Region::getDefaultFont());

        for (it = tokens.begin(); it != tokens.end(); ++it)
        {
            size_t pos;
            if ((pos = it->find('=')) != String::npos)
            {
                String field_name = it->substr(0, pos);
                String field_value = it->substr(pos + 1);
                trimString(field_name);
                trimString(field_value);
                if (field_name == "font_name")
                {
                    font.m_name = field_value;
                }
                else if (field_name == "font_size")
                {
                    font.m_size = strtol(field_value.c_str(), NULL, 0);
                }
                else if (field_name == "font_color")
                {
                    font.m_color = strtol(field_value.c_str(), NULL, 0);
                }
                else if (field_name == "bold")
                {
                    font.m_bold = (0 == _strcmpi(field_value.c_str(), "true"));
                }
                else if (field_name == "italic")
                {
                    font.m_italic = (0 == _strcmpi(field_value.c_str(), "true"));
                }
            }
        }

        ((RegionText*)region)->setFont(font);
    }

    if (region)
    {
        m_regions.push_back(region);
        redrawWindow();

        return name;
    }

    return nullptr;
}

void Impl::delRegion(const char* regName)
{
    for (auto iter = m_regions.begin(); iter != m_regions.end(); ++iter)
    {
        if ((*iter)->getName() == regName)
        {
            delete *iter;
            m_regions.erase(iter);
            if (strcmp(regName, "title") == 0)
            {
                m_regionTitle = nullptr;
            }

            redrawWindow();
            return;
        }
    }

    CARB_LOG_ERROR("Delete region not found: %s\n", regName);
}

void Impl::delAllRegions(void)
{
    for (auto iter = m_regions.begin(); iter != m_regions.end(); ++iter)
        delete *iter;

    m_regions.clear();
    m_regionTitle = nullptr;
    redrawWindow();
}

float Impl::getDpiScaleFactor()
{
    if (m_wnd)
    {
        UINT dpi = GetDpiForWindow(m_wnd);
        return dpi / 96.0f;
    }

    return 1.0f;
}

#    if PRINT_WINDOW_MESSAGE
void printWindowMessage(UINT uMsg)
{
    static int count = 0;

    count++;
    printf("Msg - %04d: %x\n", count, uMsg);
}
#    else
#        define printWindowMessage(msg) void(0)
#    endif

LRESULT Impl::processMessage(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    LRESULT result;

    printWindowMessage(uMsg);

    switch (uMsg)
    {
        case WM_SETICON:
            if (ICON_SMALL == wParam)
            {
                m_appIcon.set(reinterpret_cast<HICON>(lParam));
            }
            break;

        case WM_NCACTIVATE:
            draw();
            // When the wParam parameter is FALSE, an application should return TRUE to
            // indicate that the system should proceed with the default processing, or
            // it should return FALSE to prevent the change.
            // When wParam is TRUE, the return value is ignored.
            if (!wParam)
                return TRUE;

            return 0l;

        case WM_NCPAINT:
            return draw();

        case WM_NCHITTEST:
            return processNcHitTest(wParam, lParam);

        case WM_NCLBUTTONDOWN:
            return processNcLButtonDown(wParam, lParam);

        case WM_NCLBUTTONUP:
            return processNcLButtonUp(wParam, lParam);

        case WM_TIMER:
            return processTimer(wParam, lParam);

        case WM_SETTEXT:
            if (m_regionTitle)
            {
                std::wstring title;
                if (IsWindowUnicode(hwnd))
                {
                    title = (const wchar_t*)lParam;
                }
                else
                {
                    title = convertAnsiToUnicode((const char*)lParam, -1);
                }
                updateFileName(title.c_str());
            }
            result = CallWindowProc(m_oldProc, hwnd, uMsg, wParam, lParam);
            draw();
            return result;

        case WM_SIZE:
            unsigned int width, height;
            width = LOWORD(lParam);
            height = HIWORD(lParam);
            result = CallWindowProc(m_oldProc, hwnd, uMsg, wParam, lParam);
            {
                // TraceScope ts("WM_SIZE");
                Rect rc;
                switch (wParam)
                {
                    case SIZE_RESTORED:
                        // WM_SIZE is sent when:
                        // 1. window is restored from maximized or minimized
                        // 2. system DPI changed
                        m_windowPos.setState(WindowState::eNormal);
                        GetWindowRect(hwnd, &rc);
                        m_windowPos.setSize(rc.getSize());
                        if (m_windowPos.isSizeChanged())
                        {
                            refreshWindowRects();
                        }
                        break;

                    case SIZE_MAXIMIZED:
                        m_windowPos.setState(WindowState::eMaximized);
                        GetWindowRect(hwnd, &rc);
                        m_windowPos.setSize(rc.getSize());
                        if (m_windowPos.isSizeChanged())
                        {
                            refreshWindowRects();
                        }
                        break;

                    case SIZE_MINIMIZED:
                        m_windowPos.setState(WindowState::eMinimized);
                        break;
                }
            }
            return result;

        case WM_MOVE:
            result = CallWindowProc(m_oldProc, hwnd, uMsg, wParam, lParam);
            if (!IsIconic(hwnd))
            {
                // TraceScope ts("WM_MOVE");

                Rect rc;
                GetWindowRect(hwnd, &rc);
                m_windowPos.setCoordinate(rc.getTopLeft());
            }
            return result;

        case WM_DPICHANGED:
        {
            UINT dpi = LOWORD(wParam);
            m_dpiScaleFactor = dpi / 96.0f;
        }
        break;

        case WM_SYSCOMMAND:
            // Save the close status
            if (wParam == SC_CLOSE)
                m_appShutdown = true;
            break;
    }

    return CallWindowProc(m_oldProc, hwnd, uMsg, wParam, lParam);
}

LRESULT Impl::draw()
{
    if (!m_wnd)
    {
        return 0;
    }

    Size size = m_windowPos.getSize();

    // ReentryBlocker blocker(m_reentryLocked);
    HDC dc = GetWindowDC(m_wnd);

#    define CACHE_SCREEN_BITMAP 1
#    if CACHE_SCREEN_BITMAP
    HBITMAP memBitmap = CreateCompatibleBitmap(dc, size.cx, size.cy);
    HDC originalDC = dc;
    dc = CreateCompatibleDC(originalDC);
    HBITMAP oldBitmap = (HBITMAP)SelectObject(dc, memBitmap);
#    endif

    {
        // Draw window border
        Pen borderPen = CreatePen(PS_SOLID, 1, m_colors["border"]);
        if (m_changeWindowRegion)
        {
            PenSwitch ps(dc, &borderPen);

            int l = (m_orgBorderWidth - m_borderWidth);
            int t = 0;
            int r = size.cx - (m_orgBorderWidth - m_borderWidth) - 1;
            int b = size.cy - (m_orgBorderWidth - m_borderWidth) - 1;

            for (int i = 0; i < m_borderWidth; ++i)
            {
                MoveToEx(dc, l, t, nullptr);
                LineTo(dc, r, t);
                LineTo(dc, r, b);
                LineTo(dc, l, b);
                LineTo(dc, l, t);

                l++;
                t++;
                r--;
                b--;
            }
        }
        else
        {
            int l = 0;
            int t = 0;
            int r = size.cx - 1;
            int b = size.cy - 1;

            int i = 0;
            PenSwitch ps(dc, &borderPen);
            for (; i < m_borderWidth; ++i)
            {
                MoveToEx(dc, l, t, nullptr);
                LineTo(dc, r, t);
                LineTo(dc, r, b);
                LineTo(dc, l, b);
                LineTo(dc, l, t);

                l++;
                t++;
                r--;
                b--;
            }

            Pen clientPen = CreatePen(PS_SOLID, 1, m_colors["client"]);
            SelectPen(dc, &clientPen);
            for (; i < m_orgBorderWidth; ++i)
            {
                MoveToEx(dc, l, t, nullptr);
                LineTo(dc, l, b);
                LineTo(dc, r, b);
                LineTo(dc, r, t);

                l++;
                r--;
                b--;
            }
        }
    }

    {
        // Draw the caption area
        Rect rcCaption(m_rcCaption);
        if (!m_changeWindowRegion)
        {
            rcCaption.left -= (m_orgBorderWidth - m_borderWidth);
            rcCaption.right += (m_orgBorderWidth - m_borderWidth);
        }

        fillRect(dc, rcCaption, m_colors["caption"]);
        Pen sepPen = CreatePen(PS_SOLID, 1, mergeColor(m_colors["caption"], m_colors["border"], 0.8f));
        PenSwitch ps(dc, &sepPen);
        MoveToEx(dc, rcCaption.left, rcCaption.bottom - 1, nullptr);
        LineTo(dc, rcCaption.right, rcCaption.bottom - 1);
    }

    {
        // Draw App ICON
        m_appIcon.draw(dc, m_rcAppIcon);
    }

    // Draw regions
    {
        Point pt;
        pt.x = m_regionStart_x;
        pt.y = m_rcCaption.top + m_rcCaption.height() / 2;

        int max_x = m_rcMin.left - 50;
        for (Regions::iterator i = m_regions.begin(); i != m_regions.end(); ++i)
        {
            Region* region = *i;
            Size size = region->draw(dc, pt.x, pt.y, m_dpiScaleFactor, m_colors["caption"], max_x);
            pt.x += size.cx + 2;
            if (pt.x >= max_x)
                break;
        }
    }

    // Draw buttons
    {
        Rect rcButton;
        rcButton = m_rcMin;
        Pen buttonPen = CreatePen(PS_SOLID, 1, m_colors["button"]);
        PenSwitch ps(dc, &buttonPen);
        int penWidth, len, x, y, i;

        // Draw the min button

        penWidth = 2;
        if (m_lastHit == HTMINBUTTON)
        {
            // Hovered
            if (m_curClicked == HTMINBUTTON)
                fillRect(dc, m_rcMin, m_colors["min_clicked"]);
            else
                fillRect(dc, m_rcMin, m_colors["min"]);
            setHovered();
            penWidth = 3;
        }

        len = int(rcButton.width() * .25f);
        x = rcButton.left + int((rcButton.width() - len) * .5f);
        if (IsZoomed(m_wnd))
            y = rcButton.top + int(rcButton.height() * .65f);
        else
            y = rcButton.top + int(rcButton.height() * .55f);

        for (i = 0; i < penWidth; ++i)
        {
            MoveToEx(dc, x, y + i, nullptr);
            LineTo(dc, x + len, y + i);
        }

        // Draw MAX button
        penWidth = 2;
        rcButton.shift(m_rcMax.left - rcButton.left, 0);

        if (m_lastHit == HTMAXBUTTON)
        {
            if (m_curClicked == HTMAXBUTTON)
                fillRect(dc, m_rcMax, m_colors["max_clicked"]);
            else
                fillRect(dc, m_rcMax, m_colors["max"]);
            setHovered();
        }

        // Maximized
        if (IsZoomed(m_wnd))
        {
            // Draw restore icon
            int d1 = int(rcButton.width() * .06f);
            int d2 = int(rcButton.width() * .18f);
            int d3 = int(rcButton.width() * .24f);

            x = rcButton.left + int(rcButton.width() * .4f);
            y = rcButton.top + (rcButton.height() - d3) * 2 / 3;

            for (i = 0; i < penWidth; ++i)
            {
                MoveToEx(dc, x + i, y + d1 + i, nullptr);
                LineTo(dc, x + i, y + d3 - i);
                LineTo(dc, x + d2 - i, y + d3 - i);
                LineTo(dc, x + d2 - i, y + d1 + i);
                LineTo(dc, x + i, y + d1 + i);

                MoveToEx(dc, x + d2, y + d2 - i, nullptr);
                LineTo(dc, x + d3 - i, y + d2 - i);
                LineTo(dc, x + d3 - i, y + i);
                LineTo(dc, x + d1 + i, y + i);
                LineTo(dc, x + d1 + i, y + d1);
            }
        }
        else
        {
            // Draw max button
            len = int(rcButton.width() * .23f);
            x = rcButton.left + int(rcButton.width() * .4f);
            y = rcButton.top + (rcButton.height() - len) / 2;

            for (i = 0; i < penWidth; ++i)
            {
                MoveToEx(dc, x + i, y + i, nullptr);
                LineTo(dc, x + i, y + len - i);
                LineTo(dc, x + len - i, y + len - i);
                LineTo(dc, x + len - i, y + i);
                LineTo(dc, x + i, y + i);
            }
        }

        // Draw the close button
        rcButton.shift(m_rcClose.left - rcButton.left, 0);
        if (m_lastHit == HTCLOSE)
        {
            // Hovered
            if (m_curClicked == HTCLOSE)
                fillRect(dc, m_rcClose, m_colors["close_clicked"]);
            else
                fillRect(dc, m_rcClose, m_colors["close"]);
            setHovered();
        }

        len = int(rcButton.width() * .25f);
        x = rcButton.left + int(rcButton.width() * .4f);
        if (IsZoomed(m_wnd))
            y = rcButton.top + int((rcButton.height() - len) * 0.70f);
        else
            y = rcButton.top + int((rcButton.height() - len) * 0.55f);

        MoveToEx(dc, x, y, nullptr);
        LineTo(dc, x + len, y + len);
        MoveToEx(dc, x, y + 1, nullptr);
        LineTo(dc, x + len - 1, y + len);
        MoveToEx(dc, x + 1, y, nullptr);
        LineTo(dc, x + len, y + len - 1);

        MoveToEx(dc, x + len - 1, y, nullptr);
        LineTo(dc, x - 1, y + len);
        MoveToEx(dc, x - 1 + len, y + 1, nullptr);
        LineTo(dc, x, y + len);
        MoveToEx(dc, x + len - 2, y, nullptr);
        LineTo(dc, x - 1, y + len - 1);
    }

#    if CACHE_SCREEN_BITMAP
    BitBlt(originalDC, 0, 0, size.cx, size.cy, dc, 0, 0, SRCCOPY);

    // Cleanup.
    SelectObject(dc, oldBitmap);
    DeleteObject(memBitmap);
    DeleteDC(dc);
    dc = originalDC;
#    endif

    return 0;
}

LRESULT Impl::processNcHitTest(WPARAM wParam, LPARAM lParam)
{
    LRESULT result = CallWindowProc(m_oldProc, m_wnd, WM_NCHITTEST, wParam, lParam);
    switch (result)
    {
        case HTCAPTION:
        case HTCLOSE:
        case HTMINBUTTON:
        case HTMAXBUTTON:
            Point pt;
            pt.x = GET_X_LPARAM(lParam);
            pt.y = GET_Y_LPARAM(lParam);
            convertScreenToWindow(pt);

            if (m_rcButtons.isPtInside(pt))
            {
                result = HTCAPTION;
                if (pt.x < m_rcMax.left)
                    result = HTMINBUTTON;
                else if (pt.x < m_rcClose.left)
                    result = HTMAXBUTTON;
                else
                    result = HTCLOSE;
            }

            if (m_lastHit != result)
            {
                m_lastHit = result;
                redrawWindow();
            }

            break;
    }

    return result;
}

LRESULT Impl::processNcLButtonDown(WPARAM wParam, LPARAM lParam)
{
    m_curClicked = m_lastHit;
    // wParam saved the last NCHITTEST result.
    if (!m_respondOnMouseUp)
        return respondButton(WM_NCLBUTTONDOWN, wParam, lParam);

    switch (m_lastHit)
    {
        case HTMINBUTTON:
        case HTMAXBUTTON:
        case HTCLOSE:
            redrawWindow();
            return 0;
    }

    return CallWindowProc(m_oldProc, m_wnd, WM_NCLBUTTONDOWN, wParam, lParam);
}

LRESULT Impl::processNcLButtonUp(WPARAM wParam, LPARAM lParam)
{
    if (m_respondOnMouseUp && (m_curClicked == m_lastHit))
    {
        LRESULT result = respondButton(WM_NCLBUTTONUP, wParam, lParam);
        m_curClicked = HTNOWHERE;
        return result;
    }
    else
    {
        m_curClicked = HTNOWHERE;
        return CallWindowProc(m_oldProc, m_wnd, WM_NCLBUTTONUP, wParam, lParam);
    }
}

LRESULT Impl::processTimer(WPARAM wParam, LPARAM lParam)
{
    if (wParam == HOVER_TIMER_ID)
    {
        Point pt;
        GetCursorPos(&pt);
        convertScreenToWindow(pt);

        if (!m_rcButtons.isPtInside(pt))
        {
            m_lastHit = HTCAPTION;
            redrawWindow();
            cleanHovered();
        }

        return 0;
    }

    return CallWindowProc(m_oldProc, m_wnd, WM_TIMER, wParam, lParam);
}

LRESULT Impl::respondButton(UINT uMsg, WPARAM wParam, LPARAM lParam)
{
    switch (m_curClicked)
    {
        case HTMINBUTTON:
            ShowWindow(m_wnd, SW_MINIMIZE);
            return 0;
        case HTMAXBUTTON:
            if (IsZoomed(m_wnd))
                ShowWindow(m_wnd, SW_RESTORE);
            else
                ShowWindow(m_wnd, SW_MAXIMIZE);
            return 0;
        case HTCLOSE:
            PostMessage(m_wnd, WM_CLOSE, 0, 0);
            m_appShutdown = true;
            return 0;
    }

    return CallWindowProc(m_oldProc, m_wnd, uMsg, wParam, lParam);
}

void Impl::initWindowRects()
{
    // Get Window rect
    Rect rcWindow;
    GetWindowRect(m_wnd, &rcWindow);
    m_windowPos.setCoordinate(rcWindow.getTopLeft());
    m_windowPos.setSize(rcWindow.getSize());

    if (IsIconic(m_wnd))
        m_windowPos.setState(WindowState::eMinimized);
    else if (IsZoomed(m_wnd))
        m_windowPos.setState(WindowState::eMaximized);
    else
        m_windowPos.setState(WindowState::eNormal);

    refreshWindowRects();
}

void Impl::refreshWindowRects()
{
    if (!m_wnd || IsIconic(m_wnd))
        return;

    // Current window size
    Rect rcWindow;
    const Size& sizeWindow = m_windowPos.getSize();
    ::GetWindowRect(m_wnd, &rcWindow);
    assert(sizeWindow == rcWindow.getSize());

    {
        // Get the client size, then caculate the margins and caption height
        Rect rcClient;
        GetClientRect(m_wnd, &rcClient);
        m_orgBorderWidth = (sizeWindow.cx - rcClient.width()) / 2;
        m_captionHeight = sizeWindow.cy - rcClient.height() - m_orgBorderWidth - m_borderWidth;
#    ifdef DEBUG_CODE
        Point lt(0, 0), br = rcClient.getBottomRight();
        ::ClientToScreen(m_wnd, &lt);
        ::ClientToScreen(m_wnd, &br);
        DBG_PRINT("Window rect: %d, %d, %d, %d\n", rcWindow.left, rcWindow.top, rcWindow.right, rcWindow.bottom);
        DBG_PRINT("Client rect: %d, %d, %d, %d\n", lt.x, lt.y, br.x, br.y);
        DBG_PRINT("Original border: %d, border: %d\n", m_orgBorderWidth, m_borderWidth);
        DBG_PRINT("Caption height: %d\n", m_captionHeight);
#    endif
    }

    {
        // Caption
        m_rcCaption.left = m_orgBorderWidth;
        m_rcCaption.top = m_borderWidth;
        m_rcCaption.right = sizeWindow.cx - m_orgBorderWidth;
        m_rcCaption.bottom = m_captionHeight + m_rcCaption.top;
    }

    {
        // Area for App Icon
        m_rcAppIcon = m_rcCaption;
        int iconSize = m_rcAppIcon.height();
        m_rcAppIcon.right = m_rcAppIcon.left + iconSize;

        iconSize = lround(iconSize * 0.57f);
        m_rcAppIcon = m_rcAppIcon.getCenterRect(iconSize, iconSize);

        // Region area
        m_regionStart_x = m_rcCaption.left + m_rcCaption.height();
    }

    {
        int w = (int)round(m_rcCaption.height() * 1.55f);
        // Area for control buttons
        m_rcClose.left = m_rcCaption.right - w;
        m_rcClose.top = m_rcCaption.top;
        m_rcClose.right = m_rcClose.left + w;
        m_rcClose.bottom = m_rcCaption.bottom - 1;

        m_rcMax = m_rcClose;
        m_rcMax.shift(-w, 0);

        m_rcMin = m_rcMax;
        m_rcMin.shift(-w, 0);

        m_rcButtons = m_rcMin;
        m_rcButtons.right = m_rcClose.right;
    }

    if (m_changeWindowRegion)
    {
        ReentryBlocker blocker(m_reentryLocked);

        // Calculate the Rgn, remove the margin from left, right, bottom
        Rect rc;
        rc.left = m_orgBorderWidth - m_borderWidth;
        rc.right = sizeWindow.cx - (m_orgBorderWidth - m_borderWidth);
        rc.top = 0;
        rc.bottom = sizeWindow.cy - (m_orgBorderWidth - m_borderWidth);
        HRGN wndRgn = CreateRectRgnIndirect(&rc);
        DBG_PRINT("Change Window Rgn\n");
        SetWindowRgn(m_wnd, wndRgn, true);
    }
    else
    {
        DBG_PRINT("Remove Window Rgn\n");
        SetWindowRgn(m_wnd, NULL, true);
    }

    m_windowPos.clearChangeFlag();
    redrawWindow();
    DBG_PRINT("Modifier started!\n");
}

WindowModifier* WindowModifier::create()
{
    return Impl::create();
}


} // namespace modifier
} // namespace omni


#else // _WIN32
namespace omni
{
namespace modifier
{
WindowModifier* WindowModifier::create()
{
    return nullptr;
}
} // namespace modifier
} // namespace omni
#endif
