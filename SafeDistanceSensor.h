#pragma once

#include "Carla/Sensor/Sensor.h"
#include "Carla/Actor/ActorDefinition.h"
#include "Carla/Actor/ActorDescription.h"
#include "Components/SphereComponent.h"
#include "SafeDistanceSensor.generated.h"

// Struct to store shared walker data
USTRUCT()
struct FSharedWalkerData
{
    GENERATED_BODY()

    int32 WalkerID; // Unique ID of the walker
    FVector Location; // Walker's location
    float Timestamp; // Time when the walker was detected
    int32 TTL; // Time-to-live for data propagation

    FSharedWalkerData() : WalkerID(-1), Location(FVector::ZeroVector), Timestamp(0.0f), TTL(3) {}
    FSharedWalkerData(int32 InWalkerID, FVector InLocation, float InTimestamp, int32 InTTL)
        : WalkerID(InWalkerID), Location(InLocation), Timestamp(InTimestamp), TTL(InTTL) {}
};

UCLASS()
class CARLA_API ASafeDistanceSensor : public ASensor
{
    GENERATED_BODY()

public:
    ASafeDistanceSensor(const FObjectInitializer& ObjectInitializer);

    static FActorDefinition GetSensorDefinition();

    void Set(const FActorDescription& ActorDescription) override;

    void SetOwner(AActor* Owner) override;

    virtual void PrePhysTick(float DeltaSeconds) override;

private:
    // Helper function to calculate the distance between two actors
    float CalculateDistance(const AActor* Actor1, const AActor* Actor2) const;

    // Broadcast walker data to nearby vehicles
    void BroadcastWalkerData(const FSharedWalkerData& WalkerData);

    // Receive and process walker data from other vehicles
    void ReceiveWalkerData(const FSharedWalkerData& WalkerData);

    // Forward walker data to other vehicles with reduced TTL
    void ForwardWalkerData(const FSharedWalkerData& WalkerData);

    UPROPERTY()
    USphereComponent* Sphere = nullptr;

    // Map storing walkers: Key (Walker ID) → Struct (Walker data)
    TMap<int32, FSharedWalkerData> TrackedWalkers;
};