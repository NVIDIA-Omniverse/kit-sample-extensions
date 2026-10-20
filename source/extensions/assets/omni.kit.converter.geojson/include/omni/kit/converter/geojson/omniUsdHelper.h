// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

// #include <iostream>
// #include <mutex>
// #include <string>

// #include <OmniClient.h>
// #include <OmniUsdLive.h>

// // TODO: Logging with a mutex is inefficient for high logging levels. A spin
// // lock might be more appropriate because there is little overhead for little
// // congestion and the critical section is lightweight
// class Log {
// public:
//   static Log &get(void) {
//     static Log log;
//     return log;
//   }

//   void to_stdout(std::string const &msg) {
//     std::unique_lock lock{m_mutex};
//     std::cout << msg;
//   }

//   void to_stderr(std::string const &msg) {
//     std::unique_lock lock{m_mutex};
//     std::cerr << msg;
//   }

// private:
//   Log(){};
//   ~Log(){};
//   Log(Log const &cpy) = delete;
//   Log(Log const &&cpy) = delete;
//   Log &operator=(Log const &cpy) = delete;
//   Log &operator=(Log const &&cpy) = delete;

//   std::mutex m_mutex;
// };

// // Omniverse Log callback
// static void logCallback(const char *threadName, const char *component,
//                         OmniClientLogLevel level,
//                         const char *message) noexcept {
//   Log::get().to_stdout(std::string(message) + '\n');
// }

// // Startup Omniverse
// static bool startOmniverse(bool const enable_live = false) {
//   // Register a function to be called whenever the library wants to print
//   // something to a log
//   omniClientSetLogCallback(logCallback);

//   // The default log level is "Info", set it to "Debug" to see all messages
//   // omniClientSetLogLevel(eOmniClientLogLevel_Warning);
//   omniClientSetLogLevel(eOmniClientLogLevel_Info);

//   // Initialize the library and pass it the version constant defined in
//   // OmniClient.h This allows the library to verify it was built with a
//   // compatible version. It will return false if there is a version mismatch.
//   if (!omniClientInitialize(kOmniClientVersion))
//     throw std::runtime_error("Failed to initialize Omniverse");

//   // Enable live updates
//   omniUsdLiveSetDefaultEnabled(enable_live);

//   return true;
// }

// // Shut down Omniverse connection
// static void shutdownOmniverse() {
//   // Calling this prior to shutdown ensures that all pending live updates
//   // complete.
//   omniUsdLiveWaitForPendingUpdates();

//   // omniClientTick(1000);
//   omniClientShutdown();
// }
