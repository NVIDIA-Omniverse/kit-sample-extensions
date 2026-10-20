// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.
#include "ConjugateGradientNormalEquations.h"

#include <algorithm>
#include <cassert>
#include <cstdio>
#include <cuda.h> // CUDA_VERSION
#include <cuda_runtime.h>
#include <type_traits>

namespace newton
{

template <class ValueT, class IndexT>
ConjugateGradientNormalEquations<ValueT, IndexT>::ConjugateGradientNormalEquations(
    int64_t rows, int64_t cols, int64_t nnz, const IndexT* cooRowInd, const IndexT* cooColInd, const ValueT* cooValues)
    : rows(rows), cols(cols), nnz(nnz), cooRowInd(cooRowInd), cooColInd(cooColInd), cooValues(cooValues)
{
    cublasHandle = 0;
    cublasStatus_t cublasStatus = cublasCreate(&cublasHandle);
    assert(cublasStatus == CUBLAS_STATUS_SUCCESS);

    cusparseHandle = 0;
    cusparseStatus_t cusparseStatus = cusparseCreate(&cusparseHandle);
    assert(cusparseStatus == CUSPARSE_STATUS_SUCCESS);
}

template <class ValueT, class IndexT>
ConjugateGradientNormalEquations<ValueT, IndexT>::~ConjugateGradientNormalEquations()
{
    cusparseDestroy(cusparseHandle);
    cusparseHandle = 0;
    cublasDestroy(cublasHandle);
    cublasHandle = 0;
}

namespace
{

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, float>::value>* = nullptr>
cublasStatus_t cublasAxpy(cublasHandle_t handle, int n, const ValueT* alpha, const ValueT* x, int incx, ValueT* y, int incy)
{
    return cublasSaxpy(handle, n, alpha, x, incx, y, incy);
}

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, double>::value>* = nullptr>
cublasStatus_t cublasAxpy(cublasHandle_t handle, int n, const ValueT* alpha, const ValueT* x, int incx, ValueT* y, int incy)
{
    return cublasDaxpy(handle, n, alpha, x, incx, y, incy);
}

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, float>::value>* = nullptr>
cublasStatus_t cublasDot(cublasHandle_t handle, int n, const ValueT* x, int incx, const ValueT* y, int incy, ValueT* result)
{
    return cublasSdot(handle, n, x, incx, y, incy, result);
}

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, double>::value>* = nullptr>
cublasStatus_t cublasDot(cublasHandle_t handle, int n, const ValueT* x, int incx, const ValueT* y, int incy, ValueT* result)
{
    return cublasDdot(handle, n, x, incx, y, incy, result);
}

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, float>::value>* = nullptr>
cublasStatus_t cublasScal(cublasHandle_t handle, int n, const ValueT* alpha, ValueT* x, int incx)
{
    return cublasSscal(handle, n, alpha, x, incx);
}

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, double>::value>* = nullptr>
cublasStatus_t cublasScal(cublasHandle_t handle, int n, const ValueT* alpha, ValueT* x, int incx)
{
    return cublasDscal(handle, n, alpha, x, incx);
}

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, float>::value>* = nullptr>
cublasStatus_t cublasCopy(cublasHandle_t handle, int n, const ValueT* x, int incx, ValueT* y, int incy)
{
    return cublasScopy(handle, n, x, incx, y, incy);
}

template <class ValueT, typename std::enable_if_t<std::is_same<ValueT, double>::value>* = nullptr>
cublasStatus_t cublasCopy(cublasHandle_t handle, int n, const ValueT* x, int incx, ValueT* y, int incy)
{
    return cublasDcopy(handle, n, x, incx, y, incy);
}

}

template <class ValueT, class IndexT>
void ConjugateGradientNormalEquations<ValueT, IndexT>::solve(
    ValueT* x, const ValueT* rhs, ValueT relative_tolerance, ValueT absolute_tolerance, int max_iterations) const
{
    // We guard with a cuda version check because, for whatever reason, some of the cusparse functions are not
    // defined in the cuda 10 version of the cusparse library (even though they are declared in the cusparse header).
#if CUDA_VERSION >= 11000
    constexpr cudaDataType_t valueType = std::is_same<ValueT, float>::value ? CUDA_R_32F : CUDA_R_64F;
    constexpr cusparseIndexType_t idxType =
        std::is_same<IndexT, int32_t>::value ? CUSPARSE_INDEX_32I : CUSPARSE_INDEX_64I;

    ValueT* p = nullptr;
    ValueT* Gx = nullptr;
    ValueT* GTGx = nullptr;
    ValueT* r = nullptr;
    ValueT* GTr = nullptr;

    cudaError_t cudaStatus = cudaMalloc(&p, cols * sizeof(ValueT));
    cudaStatus = cudaMalloc(&Gx, rows * sizeof(ValueT));
    cudaStatus = cudaMemset(Gx, 0, rows * sizeof(ValueT)); // required to avoid an uninitialized read warning
    cudaStatus = cudaMalloc(&GTGx, cols * sizeof(ValueT));
    cudaStatus = cudaMemset(GTGx, 0, cols * sizeof(ValueT)); // required to avoid an uninitialized read warning
    cudaStatus = cudaMalloc(&r, rows * sizeof(ValueT));
    cudaStatus = cudaMalloc(&GTr, cols * sizeof(ValueT));
    cudaStatus = cudaMemcpy(r, rhs, rows * sizeof(ValueT), cudaMemcpyDefault);

    cusparseSpMatDescr_t matA = nullptr;
    cusparseCreateCoo(&matA, rows, cols, nnz, const_cast<IndexT*>(cooRowInd), const_cast<IndexT*>(cooColInd),
                      const_cast<ValueT*>(cooValues), idxType, CUSPARSE_INDEX_BASE_ZERO, valueType);
    cusparseDnVecDescr_t vecx = nullptr;
    cusparseCreateDnVec(&vecx, cols, x, valueType);
    cusparseDnVecDescr_t vecp = nullptr;
    cusparseCreateDnVec(&vecp, cols, p, valueType);
    cusparseDnVecDescr_t vecGx = nullptr;
    cusparseCreateDnVec(&vecGx, rows, Gx, valueType);
    cusparseDnVecDescr_t vecGTGx = nullptr;
    cusparseCreateDnVec(&vecGTGx, cols, GTGx, valueType);
    cusparseDnVecDescr_t vecr = nullptr;
    cusparseCreateDnVec(&vecr, rows, r, valueType);
    cusparseDnVecDescr_t vecGTr = nullptr;
    cusparseCreateDnVec(&vecGTr, cols, GTr, valueType);

    ValueT alpha = 1.0;
    ValueT alpham1 = -1.0;
    ValueT beta = 0.0;
    ValueT r0 = 0.;
    ValueT r1 = 0.;

#    if CUDA_VERSION >= 11000
    cusparseSpMVAlg_t alg = CUSPARSE_SPMV_ALG_DEFAULT;
#    else
    cusparseSpMVAlg_t alg = CUSPARSE_MV_ALG_DEFAULT;
#    endif

    size_t bufferSize0 = 0;
    cusparseSpMV_bufferSize(cusparseHandle, CUSPARSE_OPERATION_NON_TRANSPOSE, &alpha, matA, vecx, &beta, vecGx,
                            valueType, alg, &bufferSize0);
    void* buffer0 = nullptr;
    cudaMalloc(&buffer0, bufferSize0);

    size_t bufferSize1 = 0;
    cusparseSpMV_bufferSize(cusparseHandle, CUSPARSE_OPERATION_TRANSPOSE, &alpha, matA, vecGx, &beta, vecGTGx,
                            valueType, alg, &bufferSize1);
    void* buffer1 = nullptr;
    cudaMalloc(&buffer1, bufferSize1);

    cusparseSpMV(
        cusparseHandle, CUSPARSE_OPERATION_TRANSPOSE, &alpha, matA, vecr, &beta, vecGTr, valueType, alg, buffer1);
    cublasStatus_t cublasStatus = cublasDot(cublasHandle, cols, GTr, 1, GTr, 1, &r1);
    assert(cublasStatus == CUBLAS_STATUS_SUCCESS);
    cudaDeviceSynchronize();

    ValueT tolerance = std::max(relative_tolerance * (ValueT)sqrt(r1), absolute_tolerance);

    cusparseSpMV(
        cusparseHandle, CUSPARSE_OPERATION_NON_TRANSPOSE, &alpha, matA, vecx, &beta, vecGx, valueType, alg, buffer0);
    cusparseSpMV(
        cusparseHandle, CUSPARSE_OPERATION_TRANSPOSE, &alpha, matA, vecGx, &beta, vecGTGx, valueType, alg, buffer1);
    cublasAxpy(cublasHandle, cols, &alpham1, GTGx, 1, GTr, 1);
    cublasStatus = cublasDot(cublasHandle, cols, GTr, 1, GTr, 1, &r1);
    assert(cublasStatus == CUBLAS_STATUS_SUCCESS);
    cudaDeviceSynchronize();

    int k = 1;

    ValueT dot;
    ValueT a, b, na;

    while (r1 > tolerance * tolerance && k <= max_iterations)
    {
        if (k > 1)
        {
            b = r1 / r0;
            cublasStatus = cublasScal(cublasHandle, cols, &b, p, 1);
            cublasStatus = cublasAxpy(cublasHandle, cols, &alpha, GTr, 1, p, 1);
        }
        else
        {
            cublasStatus = cublasCopy(cublasHandle, cols, GTr, 1, p, 1);
        }

        cusparseSpMV(cusparseHandle, CUSPARSE_OPERATION_NON_TRANSPOSE, &alpha, matA, vecp, &beta, vecGx, valueType, alg,
                     buffer0);
        cusparseSpMV(
            cusparseHandle, CUSPARSE_OPERATION_TRANSPOSE, &alpha, matA, vecGx, &beta, vecGTGx, valueType, alg, buffer1);
        cublasStatus = cublasDot(cublasHandle, cols, p, 1, GTGx, 1, &dot);
        a = r1 / dot;

        cublasStatus = cublasAxpy(cublasHandle, cols, &a, p, 1, x, 1);
        na = -a;
        cublasStatus = cublasAxpy(cublasHandle, cols, &na, GTGx, 1, GTr, 1);

        r0 = r1;
        cublasStatus = cublasDot(cublasHandle, cols, GTr, 1, GTr, 1, &r1);
        cudaDeviceSynchronize();
        // printf("iteration = %3d, residual = %e\n", k, sqrt(r1));
        k++;
    }

    cudaFree(buffer1);
    cudaFree(buffer0);

    cusparseDestroyDnVec(vecGTr);
    cusparseDestroyDnVec(vecr);
    cusparseDestroyDnVec(vecGTGx);
    cusparseDestroyDnVec(vecGx);
    cusparseDestroyDnVec(vecp);
    cusparseDestroyDnVec(vecx);
    cusparseDestroySpMat(matA);

    cudaFree(GTr);
    cudaFree(r);
    cudaFree(Gx);
    cudaFree(GTGx);
    cudaFree(p);
#endif // CUDA_VERSION check
}

template class ConjugateGradientNormalEquations<float, int32_t>;
template class ConjugateGradientNormalEquations<double, int32_t>;
template class ConjugateGradientNormalEquations<float, int64_t>;
template class ConjugateGradientNormalEquations<double, int64_t>;

}
