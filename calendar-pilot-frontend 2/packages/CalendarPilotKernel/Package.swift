// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "CalendarPilotKernel",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "CalendarPilotKernel", targets: ["CalendarPilotKernel"]),
        .executable(name: "CalendarPilotDemo", targets: ["CalendarPilotDemo"]),
        .executable(name: "CalendarPilotKernelServer", targets: ["CalendarPilotKernelServer"]),
        .executable(name: "CalendarPilotEventKitBridge", targets: ["CalendarPilotEventKitBridge"]),
        .executable(name: "CalendarPilotMacApp", targets: ["CalendarPilotMacApp"])
    ],
    targets: [
        .target(name: "CalendarPilotKernel"),
        .executableTarget(name: "CalendarPilotDemo", dependencies: ["CalendarPilotKernel"]),
        .executableTarget(name: "CalendarPilotKernelServer", dependencies: ["CalendarPilotKernel"]),
        .executableTarget(
            name: "CalendarPilotEventKitBridge",
            dependencies: ["CalendarPilotKernel"],
            exclude: ["Info.plist"],
            linkerSettings: [
                .unsafeFlags([
                    "-Xlinker", "-sectcreate",
                    "-Xlinker", "__TEXT",
                    "-Xlinker", "__info_plist",
                    "-Xlinker", "Sources/CalendarPilotEventKitBridge/Info.plist",
                ])
            ]
        ),
        .executableTarget(name: "CalendarPilotMacApp"),
        .testTarget(name: "CalendarPilotKernelTests", dependencies: ["CalendarPilotKernel"])
    ]
)
