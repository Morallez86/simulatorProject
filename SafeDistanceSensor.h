#pragma once

#include "Carla/Sensor/Sensor.h"
#include "Carla/Actor/ActorDefinition.h"
#include "Carla/Actor/ActorDescription.h"
#include "Components/SphereComponent.h"
#include "GameFramework/Actor.h"
#include "SafeDistanceSensor.generated.h"

// Struct to store shared walker data
USTRUCT()
struct FSharedWalkerData
{
    GENERATED_BODY()

    int32 WalkerID;
    FVector Location;
    float Timestamp;

    FSharedWalkerData() : WalkerID(-1), Location(FVector::ZeroVector), Timestamp(0.0f) {}
    FSharedWalkerData(int32 InWalkerID, FVector InLocation, float InTimestamp)
        : WalkerID(InWalkerID), Location(InLocation), Timestamp(InTimestamp) {}
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

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    void PerformLineTrace(float DeltaSeconds);
    void UpdateWalkerData(int32 WalkerID, const FVector& Location, float Timestamp);
    void PeriodicBroadcast();

    UFUNCTION(BlueprintCallable, Category = "SafeDistanceSensor")
    TArray<FVector> GetTrackedWalkerLocations() const;

    UPROPERTY()
    USphereComponent* Sphere = nullptr;

    TMap<int32, FSharedWalkerData> TrackedWalkers;
    FTimerHandle BroadcastTimerHandle;
    FCriticalSection DataLock;

    float TraceRange;
    float CurrentHorizontalAngle;
};
