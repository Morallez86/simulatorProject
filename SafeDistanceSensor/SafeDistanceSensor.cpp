#include "Carla.h"
#include "Carla/Sensor/SafeDistanceSensor.h"

#include "Carla/Actor/ActorBlueprintFunctionLibrary.h"
#include "Carla/Game/CarlaEpisode.h"
#include "Carla/Util/BoundingBoxCalculator.h"
#include "Carla/Vehicle/CarlaWheeledVehicle.h"

ASafeDistanceSensor::ASafeDistanceSensor(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    Box = CreateDefaultSubobject<UBoxComponent>(TEXT("BoxOverlap"));
    Box->SetupAttachment(RootComponent);
    Box->SetHiddenInGame(false); // Disable for debugging.
    Box->SetCollisionProfileName(FName("OverlapAll"));

    PrimaryActorTick.bCanEverTick = true;
}

FActorDefinition ASafeDistanceSensor::GetSensorDefinition()
{
    auto Definition = UActorBlueprintFunctionLibrary::MakeGenericSensorDefinition(
        TEXT("other"),
        TEXT("safe_distance"));

    FActorVariation Front;
    Front.Id = TEXT("safe_distance_front");
    Front.Type = EActorAttributeType::Float;
    Front.RecommendedValues = { TEXT("1.0") };
    Front.bRestrictToRecommended = false;

    FActorVariation Back;
    Back.Id = TEXT("safe_distance_back");
    Back.Type = EActorAttributeType::Float;
    Back.RecommendedValues = { TEXT("0.5") };
    Back.bRestrictToRecommended = false;

    FActorVariation Lateral;
    Lateral.Id = TEXT("safe_distance_lateral");
    Lateral.Type = EActorAttributeType::Float;
    Lateral.RecommendedValues = { TEXT("0.5") };
    Lateral.bRestrictToRecommended = false;

    Definition.Variations.Append({ Front, Back, Lateral });

    return Definition;
}

void ASafeDistanceSensor::Set(const FActorDescription& Description)
{
    Super::Set(Description);

    float Front = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat(
        "safe_distance_front", Description.Variations, 1.0f);
    float Back = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat(
        "safe_distance_back", Description.Variations, 0.5f);
    float Lateral = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat(
        "safe_distance_lateral", Description.Variations, 0.5f);

    constexpr float M_TO_CM = 100.0f;

    float LocationX = M_TO_CM * (Front - Back) / 2.0f;
    float ExtentX = M_TO_CM * (Front + Back) / 2.0f;
    float ExtentY = M_TO_CM * Lateral;

    // Assume BoundingBox.Extent.Z is accessible here
    float DesiredZOffset = -100.0f; // Example offset for debugging.

    // Debugging logs
    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Attributes - Front: %f, Back: %f, Lateral: %f"),
        Front, Back, Lateral);
    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Box LocationX: %f, ExtentX: %f, ExtentY: %f, DesiredZOffset: %f"),
        LocationX, ExtentX, ExtentY, DesiredZOffset);

    Box->SetRelativeLocation(FVector{ LocationX, 0.0f, DesiredZOffset });
    Box->SetBoxExtent(FVector{ ExtentX, ExtentY, 50.0f });

    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Final Location: %s, Extent: %s"),
        *Box->GetRelativeLocation().ToString(), *Box->GetUnscaledBoxExtent().ToString());
}

void ASafeDistanceSensor::SetOwner(AActor* Owner)
{
    Super::SetOwner(Owner);

    auto BoundingBox = UBoundingBoxCalculator::GetActorBoundingBox(Owner);

    Box->SetBoxExtent(BoundingBox.Extent + Box->GetUnscaledBoxExtent());
}

void ASafeDistanceSensor::PrePhysTick(float DeltaSeconds)
{
    Super::PrePhysTick(DeltaSeconds);

    TSet<AActor*> DetectedActors;
    Box->GetOverlappingActors(DetectedActors, ACarlaWheeledVehicle::StaticClass());
    DetectedActors.Remove(GetOwner());

    if (DetectedActors.Num() > 0)
    {
        // Debugging log to verify detected actors
        for (AActor* Actor : DetectedActors)
        {
            UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor detected actor: %s"), *Actor->GetName());
        }

        // Send data for detected actors
        auto Stream = GetDataStream(*this);
        Stream.SerializeAndSend(*this, GetEpisode(), DetectedActors);
    }
    else
    {
        UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor detected no actors in proximity."));
    }
}