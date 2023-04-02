// This file was generated by x-IMU3-GUI/Source/Windows/Graphs/generate_graph_windows.py

#include "GraphWindow.h"
#include "Ximu3.hpp"

class BatteryVoltageGraphWindow : public GraphWindow
{
public:
    BatteryVoltageGraphWindow(const juce::ValueTree& windowLayout, const juce::Identifier& type, DevicePanel& devicePanel_, GLRenderer& glRenderer);

    ~BatteryVoltageGraphWindow() override;

private:
    static Graph::Settings settings;

    std::vector<uint64_t> callbackIDs;
    std::function<void(ximu3::XIMU3_BatteryMessage)> batteryCallback;
};