#include "Carla.h"
#include "Carla/Sensor/SafeDistanceSensor.h"
#include "Carla/Actor/ActorBlueprintFunctionLibrary.h"
#include "Carla/Game/CarlaEpisode.h"
#include "Carla/Util/BoundingBoxCalculator.h"
#include "Carla/Walker/WalkerBase.h"
#include "Carla/Vehicle/CarlaWheeledVehicle.h"
#include "Kismet/GameplayStatics.h"

ASafeDistanceSensor::ASafeDistanceSensor(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("SphereOverlap"));
    Sphere->SetupAttachment(RootComponent);
    Sphere->SetHiddenInGame(false); // Debugging.
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
        "safe_distance_radius", Description.Variations, 1000.0f); // Default radius
    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Radius: %f"), Radius);

    Sphere->SetSphereRadius(Radius);
    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Final Radius: %f"), Sphere->GetScaledSphereRadius());
}

void ASafeDistanceSensor::SetOwner(AActor* NewOwner)
{
    Super::SetOwner(NewOwner);
    auto BoundingBox = UBoundingBoxCalculator::GetActorBoundingBox(NewOwner);
    Sphere->SetRelativeLocation(FVector{ 0.0f, 0.0f, BoundingBox.Extent.Z });
}

void ASafeDistanceSensor::BroadcastWalkerData(const FSharedWalkerData& WalkerData)
{
    TSet<AActor*> NearbyVehicles;
    Sphere->GetOverlappingActors(NearbyVehicles, ACarlaWheeledVehicle::StaticClass());
    NearbyVehicles.Remove(GetOwner());

    TArray<AActor*> AllSensors;
    UGameplayStatics::GetAllActorsOfClass(GetWorld(), ASafeDistanceSensor::StaticClass(), AllSensors);

    for (AActor* Vehicle : NearbyVehicles)
    {
        for (AActor* Sensor : AllSensors)
        {
            if (Sensor && Sensor->GetOwner() == Vehicle)
            {
                ASafeDistanceSensor* VehicleSensor = Cast<ASafeDistanceSensor>(Sensor);
                if (VehicleSensor)
                {
                    VehicleSensor->ReceiveWalkerData(WalkerData);
                }
            }
        }
    }
}

void ASafeDistanceSensor::ReceiveWalkerData(const FSharedWalkerData& WalkerData)
{
    if (!TrackedWalkers.Contains(WalkerData.WalkerID))
    {
        // Add new walker to the tracked list
        TrackedWalkers.Add(WalkerData.WalkerID, WalkerData);
    }
    else
    {
        // Update existing walker's data if the received data is newer
        if (WalkerData.Timestamp > TrackedWalkers[WalkerData.WalkerID].Timestamp)
        {
            TrackedWalkers[WalkerData.WalkerID] = WalkerData;
        }
    }
    // Forward data to nearby vehicles
    ForwardWalkerData(WalkerData);
}

void ASafeDistanceSensor::ForwardWalkerData(const FSharedWalkerData& WalkerData)
{
    if (WalkerData.TTL <= 0) return;
    FSharedWalkerData ForwardedData = WalkerData;
    ForwardedData.TTL--;
    BroadcastWalkerData(ForwardedData);
}

void ASafeDistanceSensor::PrePhysTick(float DeltaSeconds)
{
    Super::PrePhysTick(DeltaSeconds);
    // Detect overlapping walkers
    TSet<AActor*> DetectedWalkers;
    Sphere->GetOverlappingActors(DetectedWalkers, AWalkerBase::StaticClass());
    DetectedWalkers.Remove(GetOwner());
    float CurrentTime = GetWorld()->GetTimeSeconds();
    for (AActor* Walker : DetectedWalkers)
    {
        int32 WalkerID = Walker->GetUniqueID();
        FVector Location = Walker->GetActorLocation();
        // Create walker data
        FSharedWalkerData WalkerData(WalkerID, Location, CurrentTime, 3); // TTL = 3
        // Store walker data if not already stored
        if (!TrackedWalkers.Contains(WalkerID))
        {
            ReceiveWalkerData(WalkerData);
        }
    }
    // Detect overlapping vehicles and transmit walker data
    TSet<AActor*> NearbyVehicles;
    Sphere->GetOverlappingActors(NearbyVehicles, ACarlaWheeledVehicle::StaticClass());
    NearbyVehicles.Remove(GetOwner());
    for (AActor* Vehicle : NearbyVehicles)
    {
        for (const auto& Entry : TrackedWalkers)
        {
            BroadcastWalkerData(Entry.Value);
        }
    }
    // Cleanup: Remove walkers not seen for 20 seconds
    TArray<int32> WalkersToRemove;
    for (auto& Entry : TrackedWalkers)
    {
        if (CurrentTime - Entry.Value.Timestamp > 20.0f)
        {
            WalkersToRemove.Add(Entry.Key);
        }
    }
    for (int32 WalkerID : WalkersToRemove)
    {
        TrackedWalkers.Remove(WalkerID);
    }
}

TArray<FVector> ASafeDistanceSensor::GetTrackedWalkerLocations() const
{
    TArray<FVector> RelativeLocations;
    AActor* OwnerActor = GetOwner();
    
    if (!OwnerActor) return RelativeLocations;  // Ensure sensor has an owner (vehicle)

    FVector OwnerLocation = OwnerActor->GetActorLocation();
    UE_LOG(LogCarla, Warning, TEXT("Owner Location: %s"), *OwnerLocation.ToString());

    for (const auto& Entry : TrackedWalkers)
    {
        FVector RelativePosition = Entry.Value.Location - OwnerLocation;
        UE_LOG(LogCarla, Warning, TEXT("Walker ID: %d, Walker Location: %s, Relative Position: %s"),
            Entry.Key, *Entry.Value.Location.ToString(), *RelativePosition.ToString());
        RelativeLocations.Add(RelativePosition);
    }

    return RelativeLocations;
}

TArray<FVector> ASafeDistanceSensor::GetRadarWalkerPositions(const TArray<FVector>& WalkerPositions) const
{
    TArray<FVector> RadarPositions;
    const float RadarSize = 500.0f; // Size of the radar UI
    const float RadarRadius = RadarSize / 2.0f;
    const float DetectionRadius = 1000.0f; // Detection radius of the sensor

    for (const FVector& RelativePosition : WalkerPositions)
    {
        // Normalize the position based on detection radius
        FVector NormalizedPosition(
            RelativePosition.Y / DetectionRadius,
            RelativePosition.X / DetectionRadius,
            0.0f
        );

        // Scale to radar size
        FVector RadarPosition = NormalizedPosition * RadarRadius;

        // Offset to center the radar
        RadarPosition += FVector(RadarRadius, RadarRadius, 0.0f);

        UE_LOG(LogCarla, Warning, TEXT("Relative Position: %s, Normalized Position: %s, Radar Position: %s"),
            *RelativePosition.ToString(), *NormalizedPosition.ToString(), *RadarPosition.ToString());

        RadarPositions.Add(RadarPosition);
    }

    return RadarPositions;
}