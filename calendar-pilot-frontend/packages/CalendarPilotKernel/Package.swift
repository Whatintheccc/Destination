// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CalendarPilotKernel",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "CalendarPilotKernel", targets: ["CalendarPilotKernel"]),
        .executable(name: "CalendarPilotDemo", targets: ["CalendarPilotDemo"]),
        .executable(name: "CalendarPilotKernelServer", targets: ["CalendarPilotKernelServer"]),
        .executable(name: "CalendarPilotMacApp", targets: ["CalendarPilotMacApp"])
    ],
    targets: [
        .target(name: "CalendarPilotKernel"),
        .executableTarget(name: "CalendarPilotDemo", dependencies: ["CalendarPilotKernel"]),
        .executableTarget(name: "CalendarPilotKernelServer", dependencies: ["CalendarPilotKernel"]),
        .executableTarget(name: "CalendarPilotMacApp", dependencies: []),
        .testTarget(name: "CalendarPilotKernelTests", dependencies: ["CalendarPilotKernel"])
    ]
)
