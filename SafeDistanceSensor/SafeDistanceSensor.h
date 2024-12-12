#pragma once

#include "Carla/Sensor/Sensor.h"

#include "Carla/Actor/ActorDefinition.h"
#include "Carla/Actor/ActorDescription.h"

#include "Components/BoxComponent.h"

#include "SafeDistanceSensor.generated.h"

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

	UPROPERTY()
		UBoxComponent* Box = nullptr;
};
