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
    Sphere->SetHiddenInGame(false);
    Sphere->SetCollisionProfileName(FName("OverlapAll"));
    PrimaryActorTick.bCanEverTick = true;
}

void ASafeDistanceSensor::BeginPlay()
{
    Super::BeginPlay();
    GetWorldTimerManager().SetTimer(BroadcastTimerHandle, this, &ASafeDistanceSensor::PeriodicBroadcast, 1.0f, true);
}

void ASafeDistanceSensor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    Super::EndPlay(EndPlayReason);
    GetWorldTimerManager().ClearTimer(BroadcastTimerHandle);
}

FActorDefinition ASafeDistanceSensor::GetSensorDefinition()
{
    auto Definition = UActorBlueprintFunctionLibrary::MakeGenericSensorDefinition(TEXT("other"), TEXT("safe_distance"));

    FActorVariation Radius;
    Radius.Id = TEXT("safe_distance_radius");
    Radius.Type = EActorAttributeType::Float;
    Radius.RecommendedValues = {TEXT("500.0")};
    Radius.bRestrictToRecommended = false;
    Definition.Variations.Append({Radius});

    return Definition;
}

void ASafeDistanceSensor::Set(const FActorDescription& Description)
{
    Super::Set(Description);

    float Radius = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat("safe_distance_radius", Description.Variations, 1000.0f);
    Sphere->SetSphereRadius(Radius);
}

void ASafeDistanceSensor::SetOwner(AActor* NewOwner)
{
    Super::SetOwner(NewOwner);
    auto BoundingBox = UBoundingBoxCalculator::GetActorBoundingBox(NewOwner);
    Sphere->SetRelativeLocation(FVector{0.0f, 0.0f, BoundingBox.Extent.Z});
}

void ASafeDistanceSensor::UpdateWalkerData(int32 WalkerID, const FVector& Location, float Timestamp)
{
    FScopeLock Lock(&DataLock);
    auto* ExistingData = TrackedWalkers.Find(WalkerID);
    if (!ExistingData || Timestamp > ExistingData->Timestamp)
    {
        TrackedWalkers.Add(WalkerID, FSharedWalkerData(WalkerID, Location, Timestamp));
    }
}

void ASafeDistanceSensor::PeriodicBroadcast()
{
    FScopeLock Lock(&DataLock);
    if (TrackedWalkers.Num() == 0) return;

    TSet<AActor*> NearbyVehicles;
    Sphere->GetOverlappingActors(NearbyVehicles, ACarlaWheeledVehicle::StaticClass());
    NearbyVehicles.Remove(GetOwner());

    for (AActor* Vehicle : NearbyVehicles)
    {
        // Get all attached actors of type ASafeDistanceSensor
        TArray<AActor*> AttachedActors;
        Vehicle->GetAttachedActors(AttachedActors);

        for (AActor* AttachedActor : AttachedActors)
        {
            ASafeDistanceSensor* VehicleSensor = Cast<ASafeDistanceSensor>(AttachedActor);
            if (VehicleSensor)
            {
                for (const auto& Entry : TrackedWalkers)
                {
                    VehicleSensor->UpdateWalkerData(Entry.Key, Entry.Value.Location, Entry.Value.Timestamp);
                }
            }
        }
    }
}

void ASafeDistanceSensor::PrePhysTick(float DeltaSeconds)
{
    Super::PrePhysTick(DeltaSeconds);

    TSet<AActor*> DetectedWalkers;
    Sphere->GetOverlappingActors(DetectedWalkers, AWalkerBase::StaticClass());
    float CurrentTime = GetWorld()->GetTimeSeconds();

    for (AActor* Walker : DetectedWalkers)
    {
        UpdateWalkerData(Walker->GetUniqueID(), Walker->GetActorLocation(), CurrentTime);
    }

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
    if (!OwnerActor) return RelativeLocations;

    FVector OwnerLocation = OwnerActor->GetActorLocation();

    for (const auto& Entry : TrackedWalkers)
    {
        RelativeLocations.Add(Entry.Value.Location - OwnerLocation);
    }

    return RelativeLocations;
}