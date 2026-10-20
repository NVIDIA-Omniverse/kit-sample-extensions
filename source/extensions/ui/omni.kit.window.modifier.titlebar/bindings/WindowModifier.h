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

#include <functional>
#include <list>
#include <string>

#define NOMINMAX

namespace omni
{
namespace modifier
{

enum WindowState
{
    eNormal = 0,
    eMaximized = 1,
    eMinimized = 2,
    eInvalid = -1,
};

class WindowModifier
{
protected:
    WindowModifier(){};
    virtual ~WindowModifier(){};

public:
    static WindowModifier* create();
    void destroy()
    {
        delete this;
    }
    virtual bool start(void* hwnd) = 0;
    virtual void stop() = 0;

    // The following function can be called before start()
    virtual void setBorderWidth(int width) = 0;
    virtual void setColor(const char* category, int color) = 0;
    virtual void setDefaultFont(const char* fontName, int fontSize, int fontColor) = 0;
    virtual void setSeparator(int color, int width) = 0;
    virtual void setShowFullPath(bool value) = 0;
    virtual void setRespondOnMouseUp(bool value) = 0;
    virtual void setChangeWindowRegion(bool value) = 0;
    virtual const char* addRegion(const char* name, const char* type, const char* context, const char* attributes) = 0;
    virtual void delRegion(const char* name) = 0;
    virtual void delAllRegions(void) = 0;
};
} // namespace modifier
} // namespace omni
