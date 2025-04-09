#pragma once

#include "Carla/Sensor/Sensor.h"
#include "Carla/Actor/ActorDefinition.h"
#include "Carla/Actor/ActorDescription.h"
#include "GameFramework/Actor.h"
#include "WalkerDetectionSensor.generated.h"

// Struct to store shared walker data
USTRUCT()
struct FSharedWalkerDatas
{
    GENERATED_BODY()

    int32 WalkerID;
    FVector Location;
    float Timestamp;
    bool bDetectedByOwnVehicle;

    FSharedWalkerDatas() : WalkerID(-1), Location(FVector::ZeroVector), Timestamp(0.0f), bDetectedByOwnVehicle(false) {}
    FSharedWalkerDatas(int32 InWalkerID, FVector InLocation, float InTimestamp, bool InDetectedByOwnVehicle = false)
        : WalkerID(InWalkerID), Location(InLocation), Timestamp(InTimestamp), bDetectedByOwnVehicle(InDetectedByOwnVehicle) {}
};

UCLASS()
class CARLA_API AWalkerDetectionSensor : public ASensor
{
    GENERATED_BODY()

public:
    AWalkerDetectionSensor(const FObjectInitializer& ObjectInitializer);

    static FActorDefinition GetSensorDefinition();
    void Set(const FActorDescription& ActorDescription) override;
    void SetOwner(AActor* Owner) override;
    virtual void PrePhysTick(float DeltaSeconds) override;

    // Getter for tracked walkers
    const TMap<int32, FSharedWalkerDatas>& GetTrackedWalkers() const;
    
    void UpdateWalkerData(int32 WalkerID, const FVector& Location, float Timestamp, bool bDetectedByOwnVehicle);

    FCriticalSection& GetDataLock() { return DataLock; }

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    void PerformLineTrace(float DeltaSeconds);

    TMap<int32, FSharedWalkerDatas> TrackedWalkers;
    FCriticalSection DataLock;

    UFUNCTION(BlueprintCallable, Category = "WalkerDetectionSensor")
    TArray<FVector> GetTrackedWalkerLocations() const;

    UFUNCTION(BlueprintCallable, Category = "WalkerDetectionSensor")
    TArray<FVector> GetTrackedWalkerLocationsInWorld() const;

    UFUNCTION(BlueprintCallable, Category = "WalkerDetectionSensor")
    TArray<bool> GetDetectedByOwnVehicleFlags() const;

    float TraceRange; // Range of the line trace
    float CurrentHorizontalAngle; // Current angle of the line trace
};