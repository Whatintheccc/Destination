// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CalendarPilotKernel",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "CalendarPilotKernel", targets: ["CalendarPilotKernel"]),
        .executable(name: "CalendarPilotDemo", targets: ["CalendarPilotDemo"])
    ],
    targets: [
        .target(name: "CalendarPilotKernel"),
        .executableTarget(name: "CalendarPilotDemo", dependencies: ["CalendarPilotKernel"]),
        .testTarget(name: "CalendarPilotKernelTests", dependencies: ["CalendarPilotKernel"])
    ]
)
