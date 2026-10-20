// SPDX-FileCopyrightText: Copyright (c) 2020-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "WindowModifier.h"

#include <carb/BindingsPythonUtils.h>
#include <carb/Framework.h>

#include <type_traits>

CARB_BINDINGS("omni.kit.window.modifier.titlebar.python")

namespace
{

class Modifier
{
public:
    Modifier()
    {
#if defined(_WIN32)
        m_modifier = omni::modifier::WindowModifier::create();
#else
        m_modifier = nullptr;
#endif
    }

    ~Modifier()
    {
        if (m_modifier)
        {
            m_modifier->destroy();
            m_modifier = nullptr;
        }
    }

    void start(void* hwnd)
    {
        if (m_modifier)
        {
            m_modifier->start(hwnd);
        }
    }

    void stop()
    {
        if (m_modifier)
        {
            m_modifier->stop();
        }
    }

    // The following function can be called before start()
    void setBorderWidth(int width)
    {
        if (m_modifier)
        {
            m_modifier->setBorderWidth(width);
        }
    }

    void setColor(const char* category, int color)
    {
        if (m_modifier)
        {
            m_modifier->setColor(category, color);
        }
    }

    void setDefaultFont(const char* fontName, int fontSize, int fontColor)
    {
        if (m_modifier)
        {
            m_modifier->setDefaultFont(fontName, fontSize, fontColor);
        }
    }

    void setSeparator(int color, int width)
    {
        if (m_modifier)
        {
            m_modifier->setSeparator(color, width);
        }
    }

    void setShowFullPath(bool value)
    {
        if (m_modifier)
        {
            m_modifier->setShowFullPath(value);
        }
    }

    void setRespondOnMouseUp(bool value)
    {
        if (m_modifier)
        {
            m_modifier->setRespondOnMouseUp(value);
        }
    }

    void setChangeWindowRegion(bool value)
    {
        if (m_modifier)
        {
            m_modifier->setChangeWindowRegion(value);
        }
    }

    const char* addRegion(const char* name, const char* type, const char* context, const char* attributes)
    {
        if (m_modifier)
        {
            return m_modifier->addRegion(name, type, context, attributes);
        }

        return nullptr;
    }

    void delRegion(const char* regName)
    {
        if (m_modifier)
        {
            return m_modifier->delRegion(regName);
        }
    }

    void delAllRegions(void)
    {
        if (m_modifier)
        {
            return m_modifier->delAllRegions();
        }
    }

private:
    omni::modifier::WindowModifier* m_modifier;
};

PYBIND11_MODULE(_modifier, m)
{
    using namespace carb;

    m.doc() = "pybind11 omni.kit.window.modifier.titlebar bindings";

    py::class_<Modifier>(m, "Modifier",
                         R"(
    This class is used to modifier the titlebar: icon, font, title string, version, etc.
        )")
        .def(py::init<>())
        .def("start", &Modifier::start)
        .def("stop", &Modifier::stop)

        .def("setBorderWidth", &Modifier::setBorderWidth)
        .def("setColor", &Modifier::setColor)
        .def("setDefaultFont", &Modifier::setDefaultFont)
        .def("setSeparator", &Modifier::setSeparator)
        .def("setShowFullPath", &Modifier::setShowFullPath)
        .def("setRespondOnMouseUp", &Modifier::setRespondOnMouseUp)
        .def("setChangeWindowRegion", &Modifier::setChangeWindowRegion)
        .def("addRegion", &Modifier::addRegion)
        .def("delRegion", &Modifier::delRegion)
        .def("delAllRegions", &Modifier::delAllRegions);
}
} // namespace
