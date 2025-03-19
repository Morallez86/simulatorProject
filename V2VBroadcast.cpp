#include "Carla.h"
#include "Carla/Sensor/V2VBroadcast.h"
#include "Carla/Actor/ActorBlueprintFunctionLibrary.h"
#include "Carla/Sensor/WalkerDetectionSensor.h"
#include "Carla/Vehicle/CarlaWheeledVehicle.h"
#include "Kismet/GameplayStatics.h"
#include "DrawDebugHelpers.h"

AV2VBroadcast::AV2VBroadcast(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    PrimaryActorTick.bCanEverTick = true;
    Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("SphereOverlap"));
    Sphere->SetupAttachment(RootComponent);
    Sphere->SetHiddenInGame(false);
    Sphere->SetCollisionProfileName(FName("OverlapAll"));
    BroadcastRadius = 1000.0f; // Default broadcast radius
}

void AV2VBroadcast::BeginPlay()
{
    Super::BeginPlay();

    // Verify that the owner actor is valid
    AActor* Owner = GetOwner();
    if (!Owner)
    {
        UE_LOG(LogCarla, Error, TEXT("Owner actor is not valid"));
        return;
    }

    UE_LOG(LogCarla, Log, TEXT("Owner actor: %s"), *Owner->GetName());

    TArray<AActor*> AttachedActors;
    Owner->GetAttachedActors(AttachedActors);

    // Log the number of attached actors
    UE_LOG(LogCarla, Log, TEXT("Number of attached actors: %d"), AttachedActors.Num());

    for (AActor* Actor : AttachedActors)
    {
        UE_LOG(LogCarla, Log, TEXT("Attached actor: %s"), *Actor->GetName());
        AWalkerDetectionSensor* Sensor = Cast<AWalkerDetectionSensor>(Actor);
        if (Sensor)
        {
            SetWalkerDetectionSensor(Sensor);
            UE_LOG(LogCarla, Log, TEXT("WalkerDetectionSensor set successfully"));
            break;
        }
    }

    if (!WalkerDetectionSensor)
    {
        UE_LOG(LogCarla, Warning, TEXT("WalkerDetectionSensor not found among attached actors"));
    }

    GetWorldTimerManager().SetTimer(BroadcastTimerHandle, this, &AV2VBroadcast::PeriodicBroadcast, 1.0f, true);
}

void AV2VBroadcast::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    Super::EndPlay(EndPlayReason);
    GetWorldTimerManager().ClearTimer(BroadcastTimerHandle);
}

void AV2VBroadcast::PrePhysTick(float DeltaSeconds)
{
    Super::PrePhysTick(DeltaSeconds);
}

FActorDefinition AV2VBroadcast::GetSensorDefinition()
{
    auto Definition = UActorBlueprintFunctionLibrary::MakeGenericSensorDefinition(TEXT("other"), TEXT("v2v_broadcast"));

    FActorVariation Radius;
    Radius.Id = TEXT("broadcast_radius");
    Radius.Type = EActorAttributeType::Float;
    Radius.RecommendedValues = {TEXT("1000.0")};
    Radius.bRestrictToRecommended = false;
    Definition.Variations.Append({Radius});

    return Definition;
}

void AV2VBroadcast::Set(const FActorDescription& Description)
{
    Super::Set(Description);
    BroadcastRadius = UActorBlueprintFunctionLibrary::RetrieveActorAttributeToFloat("broadcast_radius", Description.Variations, 1000.0f);
    Sphere->SetSphereRadius(BroadcastRadius);
}

void AV2VBroadcast::SetOwner(AActor* NewOwner)
{
    Super::SetOwner(NewOwner);
}

void AV2VBroadcast::SetBroadcastRadius(float Radius)
{
    BroadcastRadius = Radius;
    Sphere->SetSphereRadius(Radius);
}

void AV2VBroadcast::SetWalkerDetectionSensor(AWalkerDetectionSensor* Sensor)
{
    WalkerDetectionSensor = Sensor;
}

void AV2VBroadcast::PeriodicBroadcast()
{
    UE_LOG(LogCarla, Log, TEXT("Periodic broadcast"));
    if (!WalkerDetectionSensor) 
    {
        UE_LOG(LogCarla, Warning, TEXT("WalkerDetectionSensor is not set"));
        return;
    }

    FScopeLock Lock(&WalkerDetectionSensor->GetDataLock());

    UE_LOG(LogCarla, Log, TEXT("After lock"));

    const TMap<int32, FSharedWalkerDatas>& TrackedWalkers = WalkerDetectionSensor->GetTrackedWalkers();
    UE_LOG(LogCarla, Log, TEXT("Number of tracked walkers: %d"), TrackedWalkers.Num());
    if (TrackedWalkers.Num() == 0) return;
    
    UE_LOG(LogCarla, Log, TEXT("Sharing walker data with %d vehicles"), TrackedWalkers.Num());

    TSet<AActor*> NearbyVehicles;
    Sphere->GetOverlappingActors(NearbyVehicles, ACarlaWheeledVehicle::StaticClass());
    NearbyVehicles.Remove(GetOwner());
    UE_LOG(LogCarla, Log, TEXT("Found %d nearby vehicles"), NearbyVehicles.Num());

    for (AActor* Vehicle : NearbyVehicles)
    {
        // Get all attached actors of type AV2VBroadcast
        TArray<AActor*> AttachedActors;
        Vehicle->GetAttachedActors(AttachedActors);

        for (AActor* AttachedActor : AttachedActors)
        {
            AV2VBroadcast* VehicleBroadcastActor = Cast<AV2VBroadcast>(AttachedActor);
            if (VehicleBroadcastActor)
            {
                // Share walker data with the nearby vehicle
                for (const auto& Entry : TrackedWalkers)
                {
                    VehicleBroadcastActor->WalkerDetectionSensor->UpdateWalkerData(Entry.Key, Entry.Value.Location, Entry.Value.Timestamp);
                    UE_LOG(LogCarla, Log, TEXT("Shared walker data with vehicle: %s"), *Vehicle->GetName());
                }
            }
        }
    }
}