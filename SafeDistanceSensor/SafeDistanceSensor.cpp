#include "Carla.h"
#include "Carla/Sensor/SafeDistanceSensor.h"

#include "Carla/Actor/ActorBlueprintFunctionLibrary.h"
#include "Carla/Game/CarlaEpisode.h"
#include "Carla/Util/BoundingBoxCalculator.h"
#include "Carla/Walker/WalkerBase.h"
#include "Carla/Vehicle/CarlaWheeledVehicle.h"

ASafeDistanceSensor::ASafeDistanceSensor(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("SphereOverlap"));
    Sphere->SetupAttachment(RootComponent);
    Sphere->SetHiddenInGame(false); // Disable for debugging.
    Sphere->SetCollisionProfileName(FName("OverlapAll"));

    PrimaryActorTick.bCanEverTick = true;
}

FActorDefinition ASafeDistanceSensor::GetSensorDefinition()
{
    auto Definition = UActorBlueprintFunctionLibrary::MakeGenericSensorDefinition(
        TEXT("other"),
        TEXT("safe_distance"));

    FActorVariation Radius;
    Radius.Id = TEXT("safe_distance_radius");
    Radius.Type = EActorAttributeType::Float;
    Radius.RecommendedValues = { TEXT("500.0") }; // Default radius in centimeters
    Radius.bRestrictToRecommended = false;

    Definition.Variations.Append({ Radius });

    return Definition;
}

void ASafeDistanceSensor::Set(const FActorDescription& Description)
{
    Super::Set(Description);

    float Radius = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat(
        "safe_distance_radius", Description.Variations, 500.0f); // Default radius in centimeters

    // Debugging logs
    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Radius: %f"), Radius);

    Sphere->SetSphereRadius(Radius);

    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Final Radius: %f"), Sphere->GetScaledSphereRadius());
}

void ASafeDistanceSensor::SetOwner(AActor* Owner)
{
    Super::SetOwner(Owner);

    auto BoundingBox = UBoundingBoxCalculator::GetActorBoundingBox(Owner);

    // Adjust the sphere's location relative to the owner's bounding box
    Sphere->SetRelativeLocation(FVector{ 0.0f, 0.0f, BoundingBox.Extent.Z });
}

float ASafeDistanceSensor::CalculateDistance(const AActor* Actor1, const AActor* Actor2) const
{
    if (Actor1 && Actor2)
    {
        return FVector::Distance(Actor1->GetActorLocation(), Actor2->GetActorLocation());
    }
    return FLT_MAX; // Return a large value if either actor is invalid
}

void ASafeDistanceSensor::PrePhysTick(float DeltaSeconds)
{
    Super::PrePhysTick(DeltaSeconds);

    // Detect overlapping walkers
    TSet<AActor*> DetectedWalkers;
    Sphere->GetOverlappingActors(DetectedWalkers, AWalkerBase::StaticClass());
    DetectedWalkers.Remove(GetOwner());

    // Update tracked walkers
    for (AActor* Walker : DetectedWalkers)
    {
        int32 WalkerID = Walker->GetUniqueID();
        FVector Location = Walker->GetActorLocation();

        if (TrackedWalkers.Contains(WalkerID))
        {
            // Reset timer if the walker is still detected
            TrackedWalkers[WalkerID].TimeSinceLastSeen = 0.0f;
        }
        else
        {
            // Add a new walker entry
            TrackedWalkers.Add(WalkerID, {Location, 0.0f});
        }
    }

    // Update timers and remove walkers not seen for more than 20 seconds
    TArray<int32> WalkersToRemove;
    for (auto& Entry : TrackedWalkers)
    {
        Entry.Value.TimeSinceLastSeen += DeltaSeconds;
        if (Entry.Value.TimeSinceLastSeen > 20.0f)
        {
            WalkersToRemove.Add(Entry.Key);
        }
    }

    for (int32 WalkerID : WalkersToRemove)
    {
        TrackedWalkers.Remove(WalkerID);
    }

    // Log tracked walkers
    for (const auto& Entry : TrackedWalkers)
    {
        UE_LOG(LogCarla, Warning, TEXT("Tracked Walker ID: %d, Location: %s, Time Since Last Seen: %.2f s"),
            Entry.Key, *Entry.Value.Location.ToString(), Entry.Value.TimeSinceLastSeen);
    }

    // Detect overlapping vehicles
    TSet<AActor*> DetectedVehicles;
    Sphere->GetOverlappingActors(DetectedVehicles, ACarlaWheeledVehicle::StaticClass());
    DetectedVehicles.Remove(GetOwner());

    if (DetectedVehicles.Num() > 0)
    {
        for (AActor* Vehicle : DetectedVehicles)
        {
            UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor detected vehicle: %s"), *Vehicle->GetName());
        }
    }

    // Send data for detected actors (walkers & vehicles)
    auto Stream = GetDataStream(*this);
    Stream.SerializeAndSend(*this, GetEpisode(), DetectedWalkers.Union(DetectedVehicles));
}
