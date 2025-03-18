#include "Carla.h"
#include "Carla/Sensor/SafeDistanceSensor.h"
#include "Carla/Actor/ActorBlueprintFunctionLibrary.h"
#include "Carla/Game/CarlaEpisode.h"
#include "Carla/Util/BoundingBoxCalculator.h"
#include "Carla/Walker/WalkerBase.h"
#include "Carla/Vehicle/CarlaWheeledVehicle.h"
#include "Kismet/GameplayStatics.h"
#include "DrawDebugHelpers.h"

ASafeDistanceSensor::ASafeDistanceSensor(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    PrimaryActorTick.bCanEverTick = true;
    Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("SphereOverlap"));
    Sphere->SetupAttachment(RootComponent);
    Sphere->SetHiddenInGame(false);
    Sphere->SetCollisionProfileName(FName("OverlapAll"));
    TraceRange = 1000.0f;
    CurrentHorizontalAngle = 0.0f;
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

    FActorVariation Range;
    Range.Id = TEXT("trace_range");
    Range.Type = EActorAttributeType::Float;
    Range.RecommendedValues = {TEXT("1000.0")};
    Range.bRestrictToRecommended = false;
    Definition.Variations.Append({Range});

    FActorVariation Radius;
    Radius.Id = TEXT("safe_distance_radius");
    Radius.Type = EActorAttributeType::Float;
    Radius.RecommendedValues = {TEXT("1000.0")};
    Radius.bRestrictToRecommended = false;
    Definition.Variations.Append({Radius});

    return Definition;
}

void ASafeDistanceSensor::Set(const FActorDescription& Description)
{
    Super::Set(Description);

    TraceRange = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat("trace_range", Description.Variations, 1000.0f);
    Sphere->SetSphereRadius(UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat("safe_distance_radius", Description.Variations, 1000.0f));
}

void ASafeDistanceSensor::SetOwner(AActor* NewOwner)
{
    Super::SetOwner(NewOwner);

    auto BoundingBox = UBoundingBoxCalculator::GetActorBoundingBox(NewOwner);
    Sphere->SetRelativeLocation(FVector{0.0f, 0.0f, BoundingBox.Extent.Z});
}

void ASafeDistanceSensor::PrePhysTick(float DeltaSeconds)
{
    Super::PrePhysTick(DeltaSeconds);
    // Perform the line trace
    PerformLineTrace(DeltaSeconds);
    // Remove old walker data
    float CurrentTime = GetWorld()->GetTimeSeconds();
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

void ASafeDistanceSensor::PerformLineTrace(float DeltaSeconds)
{
    FVector StartLocation = GetActorLocation();
    FRotator TraceRotation(0.0f, CurrentHorizontalAngle, 0.0f); // Rotate around the Z-axis (yaw)
    FVector EndLocation = StartLocation + TraceRotation.Vector() * TraceRange;
    FHitResult HitResult;
    FCollisionQueryParams TraceParams(FName(TEXT("Laser_Trace")), true, this);
    TraceParams.bTraceComplex = true;
    TraceParams.bReturnPhysicalMaterial = false;

    // Ignore the owner of the sensor
    AActor* OwnerActor = GetOwner();
    if (OwnerActor)
    {
        TraceParams.AddIgnoredActor(OwnerActor);
    }

    bool bHit = GetWorld()->LineTraceSingleByChannel(HitResult, StartLocation, EndLocation, ECC_Visibility, TraceParams);

    if (bHit)
    {
        AActor* HitActor = HitResult.GetActor();
        if (HitActor)
        {
            UE_LOG(LogTemp, Log, TEXT("Hit Actor: %s"), *HitActor->GetName());
            UE_LOG(LogTemp, Log, TEXT("Hit Location: %s"), *HitResult.ImpactPoint.ToString());
            UE_LOG(LogTemp, Log, TEXT("Hit Normal: %s"), *HitResult.ImpactNormal.ToString());
            UE_LOG(LogTemp, Log, TEXT("Hit Distance: %f"), HitResult.Distance);

            if (HitActor->IsA(AWalkerBase::StaticClass()))
            {
                UpdateWalkerData(HitActor->GetUniqueID(), HitResult.ImpactPoint, GetWorld()->GetTimeSeconds());
            }
        }
    }
    else
    {
        UE_LOG(LogTemp, Log, TEXT("No hit detected"));
    }

    // Rotate the trace for the next frame
    CurrentHorizontalAngle += DeltaSeconds * 360.0f; // Adjust the rotation speed based on DeltaSeconds
    if (CurrentHorizontalAngle >= 360.0f)
    {
        CurrentHorizontalAngle = 0.0f;
    }

    // Debug visualization
    DrawDebugLine(GetWorld(), StartLocation, EndLocation, FColor::Green, false, 0.1f, 0, 1.0f);
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