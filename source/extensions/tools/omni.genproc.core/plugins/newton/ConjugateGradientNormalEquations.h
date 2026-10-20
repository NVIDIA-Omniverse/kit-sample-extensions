// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include <cublas_v2.h>
#include <cusparse.h>

namespace newton
{

template <class ValueT, class IndexT>
class ConjugateGradientNormalEquations
{
public:
    ConjugateGradientNormalEquations(int64_t rows,
                                     int64_t cols,
                                     int64_t nnz,
                                     const IndexT* cooRowInd,
                                     const IndexT* cooColInd,
                                     const ValueT* cooValues);

    virtual ~ConjugateGradientNormalEquations();

    void solve(ValueT* x, const ValueT* rhs, ValueT relative_tolerance, ValueT absolute_tolerance, int max_iterations) const;

private:
    cublasHandle_t cublasHandle;
    cusparseHandle_t cusparseHandle;

    int64_t rows;
    int64_t cols;
    int64_t nnz;
    const IndexT* cooRowInd;
    const IndexT* cooColInd;
    const ValueT* cooValues;
};

}
