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
        "safe_distance_radius", Description.Variations, 1000.0f); // Default radius in centimeters
    // Debugging logs
    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Radius: %f"), Radius);
    Sphere->SetSphereRadius(Radius);
    UE_LOG(LogCarla, Warning, TEXT("SafeDistanceSensor Final Radius: %f"), Sphere->GetScaledSphereRadius());
}

void ASafeDistanceSensor::SetOwner(AActor* NewOwner)
{
    Super::SetOwner(NewOwner);
    auto BoundingBox = UBoundingBoxCalculator::GetActorBoundingBox(NewOwner);
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

void ASafeDistanceSensor::BroadcastWalkerData(const FSharedWalkerData& WalkerData)
{
    UE_LOG(LogCarla, Warning, TEXT("Test1"));
    
    // Find nearby vehicles and send data to them
    TSet<AActor*> NearbyVehicles;
    Sphere->GetOverlappingActors(NearbyVehicles, ACarlaWheeledVehicle::StaticClass());
    NearbyVehicles.Remove(GetOwner()); // Remove the owner vehicle
    UE_LOG(LogCarla, Warning, TEXT("Test2"));

    // Iterate through all sensors in the world
    TArray<AActor*> AllSensors;
    UWorld* World = GetWorld();
    if (World)
    {
        UGameplayStatics::GetAllActorsOfClass(World, ASafeDistanceSensor::StaticClass(), AllSensors);
    }

    // Iterate through the nearby vehicles
    for (AActor* Vehicle : NearbyVehicles)
    {
        // Check if any of the sensors are nearby this vehicle
        for (AActor* Sensor : AllSensors)
        {
            if (Sensor && Sensor->GetOwner() == Vehicle)
            {
                ASafeDistanceSensor* VehicleSensor = Cast<ASafeDistanceSensor>(Sensor);
                if (VehicleSensor)
                {
                    // Log the V2V communication when data is forwarded
                    UE_LOG(LogCarla, Warning, TEXT("Vehicle %s received walker data from vehicle %s (ID: %d)."),
                        *Vehicle->GetName(), *GetOwner()->GetName(), WalkerData.WalkerID);
                    VehicleSensor->ReceiveWalkerData(WalkerData); // Pass the data to the vehicle's sensor
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
    if (WalkerData.TTL <= 0) return; // Stop forwarding if TTL is exhausted
    FSharedWalkerData ForwardedData = WalkerData;
    ForwardedData.TTL--; // Decrease TTL before forwarding
    UE_LOG(LogCarla, Warning, TEXT("Forwarding walker data to nearby vehicles. Walker ID: %d, TTL: %d."),
        WalkerData.WalkerID, ForwardedData.TTL);
    BroadcastWalkerData(ForwardedData); // Send to nearby vehicles
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
        // Use ReceiveWalkerData to track & cascade
        ReceiveWalkerData(WalkerData);
    }
    // Cleanup: Remove walkers not seen for 20 seconds
    TArray<int32> WalkersToRemove;
    for (auto& Entry : TrackedWalkers)
    {
        if (CurrentTime - Entry.Value.Timestamp > 20.0f)
        {
            WalkersToRemove.Add(Entry.Key);
            UE_LOG(LogCarla, Warning, TEXT("Tracked Walker ID: %d, Location: %s, Time Since Last Seen: %.2f s"),
                Entry.Key, *Entry.Value.Location.ToString(), CurrentTime - Entry.Value.Timestamp);
        }
        else
        {
            // Log the walker ID, the car's position, and the distance between them
            FVector VehicleLocation = GetOwner()->GetActorLocation(); // Get the vehicle's current location
            float Distance = FVector::Distance(Entry.Value.Location, VehicleLocation);
            UE_LOG(LogCarla, Warning, TEXT("Tracked Walker ID: %d, Location: %s, Distance from Vehicle: %.2f meters, Time Since Last Seen: %.2f s"),
                Entry.Key, *Entry.Value.Location.ToString(), Distance, CurrentTime - Entry.Value.Timestamp);
        }
    }
    for (int32 WalkerID : WalkersToRemove)
    {
        TrackedWalkers.Remove(WalkerID);
    }
}