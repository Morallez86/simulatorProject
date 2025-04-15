#include "Carla.h"
#include "Carla/Sensor/WalkerDetectionSensor.h"
#include "Carla/Actor/ActorBlueprintFunctionLibrary.h"
#include "Carla/Game/CarlaEpisode.h"
#include "Carla/Walker/WalkerBase.h"
#include "Kismet/GameplayStatics.h"
#include "DrawDebugHelpers.h"

AWalkerDetectionSensor::AWalkerDetectionSensor(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    PrimaryActorTick.bCanEverTick = true;
    TraceRange = 1000.0f; // Default trace range
    CurrentHorizontalAngle = 0.0f; // Start at 0 degrees
}

void AWalkerDetectionSensor::BeginPlay()
{
    Super::BeginPlay();
}

void AWalkerDetectionSensor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    Super::EndPlay(EndPlayReason);
}

FActorDefinition AWalkerDetectionSensor::GetSensorDefinition()
{
    auto Definition = UActorBlueprintFunctionLibrary::MakeGenericSensorDefinition(TEXT("other"), TEXT("walker_detection"));

    FActorVariation Range;
    Range.Id = TEXT("trace_range");
    Range.Type = EActorAttributeType::Float;
    Range.RecommendedValues = {TEXT("1000.0")};
    Range.bRestrictToRecommended = false;
    Definition.Variations.Append({Range});

    return Definition;
}

void AWalkerDetectionSensor::Set(const FActorDescription& Description)
{
    Super::Set(Description);
    TraceRange = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat("trace_range", Description.Variations, 1000.0f);
}

void AWalkerDetectionSensor::SetOwner(AActor* NewOwner)
{
    Super::SetOwner(NewOwner);
}

void AWalkerDetectionSensor::PrePhysTick(float DeltaSeconds)
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

void AWalkerDetectionSensor::PerformLineTrace(float DeltaSeconds)
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
        if (HitActor && HitActor->IsA(AWalkerBase::StaticClass()))
        {
            UpdateWalkerData(HitActor->GetUniqueID(), HitResult.ImpactPoint, GetWorld()->GetTimeSeconds(), true);
        }
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

void AWalkerDetectionSensor::UpdateWalkerData(int32 WalkerID, const FVector& Location, float Timestamp, bool bDetectedByOwnVehicle)
{
    FScopeLock Lock(&DataLock);

    // log owner actor
    AActor* OwnerActor = GetOwner();
    if (OwnerActor)
    {
        UE_LOG(LogTemp, Log, TEXT("OWNER ACTOR: %s"), *OwnerActor->GetName());
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("Owner Actor is null"));
    }

    // Log the current tracked walkers before updating
    UE_LOG(LogTemp, Log, TEXT("Before UpdateWalkerData: Current Tracked Walkers:"));
    for (const auto& Entry : TrackedWalkers)
    {
        UE_LOG(LogTemp, Log, TEXT("  Walker ID=%d, Location=(%f, %f, %f), Timestamp=%f, DetectedByOwnVehicle=%s"),
            Entry.Key, Entry.Value.Location.X, Entry.Value.Location.Y, Entry.Value.Location.Z,
            Entry.Value.Timestamp, Entry.Value.bDetectedByOwnVehicle ? TEXT("true") : TEXT("false"));
    }

    // Find existing data for the walker
    auto* ExistingData = TrackedWalkers.Find(WalkerID);

    if (!ExistingData)
    {
        // Add new walker data if it doesn't exist
        TrackedWalkers.Add(WalkerID, FSharedWalkerDatas(WalkerID, Location, Timestamp, bDetectedByOwnVehicle));
        UE_LOG(LogTemp, Log, TEXT("Added new walker: ID=%d, Location=(%f, %f, %f), Timestamp=%f, DetectedByOwnVehicle=%s"),
            WalkerID, Location.X, Location.Y, Location.Z, Timestamp, bDetectedByOwnVehicle ? TEXT("true") : TEXT("false"));
    }
    else if (Timestamp > ExistingData->Timestamp)
    {
        // Update only the timestamp and location if the new data is more recent
        ExistingData->Location = Location;
        ExistingData->Timestamp = Timestamp;

        // Preserve the bDetectedByOwnVehicle flag if it was already true
        bool PreviousDetectedByOwnVehicle = ExistingData->bDetectedByOwnVehicle;
        ExistingData->bDetectedByOwnVehicle = PreviousDetectedByOwnVehicle || bDetectedByOwnVehicle;

        UE_LOG(LogTemp, Log, TEXT("Updated walker: ID=%d, Location=(%f, %f, %f), Timestamp=%f, DetectedByOwnVehicle=%s (Previous=%s)"),
            WalkerID, Location.X, Location.Y, Location.Z, Timestamp,
            ExistingData->bDetectedByOwnVehicle ? TEXT("true") : TEXT("false"),
            PreviousDetectedByOwnVehicle ? TEXT("true") : TEXT("false"));
    }
    else
    {
        UE_LOG(LogTemp, Log, TEXT("Ignored update for walker: ID=%d, Timestamp=%f (existing timestamp=%f)"),
            WalkerID, Timestamp, ExistingData->Timestamp);
    }

    // Log the current tracked walkers after updating
    UE_LOG(LogTemp, Log, TEXT("After UpdateWalkerData: Current Tracked Walkers:"));
    for (const auto& Entry : TrackedWalkers)
    {
        UE_LOG(LogTemp, Log, TEXT("  Walker ID=%d, Location=(%f, %f, %f), Timestamp=%f, DetectedByOwnVehicle=%s"),
            Entry.Key, Entry.Value.Location.X, Entry.Value.Location.Y, Entry.Value.Location.Z,
            Entry.Value.Timestamp, Entry.Value.bDetectedByOwnVehicle ? TEXT("true") : TEXT("false"));
    }
}

const TMap<int32, FSharedWalkerDatas>& AWalkerDetectionSensor::GetTrackedWalkers() const
{
    return TrackedWalkers;
}

TArray<FVector> AWalkerDetectionSensor::GetTrackedWalkerLocations() const
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

TArray<FVector> AWalkerDetectionSensor::GetTrackedWalkerLocationsInWorld() const
{
    TArray<FVector> WorldLocations;
    for (const auto& Entry : TrackedWalkers)
    {
        WorldLocations.Add(Entry.Value.Location);
    }
    return WorldLocations;
}

TArray<bool> AWalkerDetectionSensor::GetDetectedByOwnVehicleFlags() const
{
    TArray<bool> DetectedFlags;
    // log owner actor
    AActor* OwnerActor = GetOwner();
    if (OwnerActor)
    {
        UE_LOG(LogTemp, Log, TEXT("OWNER ACTOR: %s"), *OwnerActor->GetName());
    }
    else
    {
        UE_LOG(LogTemp, Warning, TEXT("Owner Actor is null"));
    }
    for (const auto& WalkerData : TrackedWalkers)
    {
        DetectedFlags.Add(WalkerData.Value.bDetectedByOwnVehicle);
        UE_LOG(LogTemp, Log, TEXT("Walker ID=%d, DetectedByOwnVehicle=%s"),
            WalkerData.Key, WalkerData.Value.bDetectedByOwnVehicle ? TEXT("true") : TEXT("false"));
    }
    return DetectedFlags;
}