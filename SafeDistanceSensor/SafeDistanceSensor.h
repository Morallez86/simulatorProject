#pragma once

#include "Carla/Sensor/Sensor.h"

#include "Carla/Actor/ActorDefinition.h"
#include "Carla/Actor/ActorDescription.h"

#include "Components/SphereComponent.h"

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
	// Helper function to calculate the distance between two actors
	float CalculateDistance(const AActor* Actor1, const AActor* Actor2) const;

	UPROPERTY()
	USphereComponent* Sphere = nullptr;
};
