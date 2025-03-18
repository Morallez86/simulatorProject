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
    GetWorldTimerManager().SetTimer(BroadcastTimerHandle, this, &AV2VBroadcast::PeriodicBroadcast, 1.0f, true);
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
    if (!WalkerDetectionSensor) return;

    FScopeLock Lock(&WalkerDetectionSensor->GetDataLock());

    const TMap<int32, FSharedWalkerDatas>& TrackedWalkers = WalkerDetectionSensor->GetTrackedWalkers();
    if (TrackedWalkers.Num() == 0) return;

    TSet<AActor*> NearbyVehicles;
    Sphere->GetOverlappingActors(NearbyVehicles, ACarlaWheeledVehicle::StaticClass());
    NearbyVehicles.Remove(GetOwner());

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
                }
            }
        }
    }
}