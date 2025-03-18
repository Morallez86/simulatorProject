#pragma once

#include "Carla/Sensor/Sensor.h"
#include "Carla/Actor/ActorDefinition.h"
#include "Carla/Actor/ActorDescription.h"
#include "Components/SphereComponent.h"
#include "GameFramework/Actor.h"
#include "V2VBroadcast.generated.h"

UCLASS()
class CARLA_API AV2VBroadcast : public ASensor
{
    GENERATED_BODY()

public:
    AV2VBroadcast(const FObjectInitializer& ObjectInitializer);

    static FActorDefinition GetSensorDefinition();
    void Set(const FActorDescription& ActorDescription) override;
    void SetOwner(AActor* Owner) override;

    void SetBroadcastRadius(float Radius);
    void SetWalkerDetectionSensor(class AWalkerDetectionSensor* Sensor);

protected:
    virtual void BeginPlay() override;
    virtual void PrePhysTick(float DeltaSeconds) override;

private:
    void PeriodicBroadcast();

    UPROPERTY()
    USphereComponent* Sphere = nullptr;

    UPROPERTY()
    AWalkerDetectionSensor* WalkerDetectionSensor = nullptr;

    FTimerHandle BroadcastTimerHandle;

    float BroadcastRadius; // Radius of the broadcast sphere
};