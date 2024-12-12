#include "carla/sensor/s11n/SafeDistanceSerializer.h"
#include "carla/sensor/data/SafeDistanceEvent.h"

namespace carla {
    namespace sensor {
        namespace s11n {

            SharedPtr<SensorData> SafeDistanceSerializer::Deserialize(RawData &&data) {
                return SharedPtr<SensorData>(new data::SafeDistanceEvent(std::move(data)));
            }

        } // namespace s11n
    } // namespace sensor
} // namespace carla