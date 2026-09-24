from datetime import datetime, timedelta, time
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scheduling.models import Appointment
from apps.scheduling.slot_lock import is_slot_locked

from .models import Barber, Service
from .serializers import BarberSerializer, ServiceSerializer


class BarberListView(generics.ListAPIView):
    queryset = Barber.objects.filter(is_active=True)
    serializer_class = BarberSerializer
    permission_classes = (permissions.AllowAny,)


class BarberDetailView(generics.RetrieveAPIView):
    queryset = Barber.objects.filter(is_active=True)
    serializer_class = BarberSerializer
    permission_classes = (permissions.AllowAny,)


class ServiceListView(generics.ListAPIView):
    queryset = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer
    permission_classes = (permissions.AllowAny,)


class AvailableSlotsView(APIView):
    """
    Returns available time slots for a specific barber, date, and service.
    Expects query parameters:
      - date: YYYY-MM-DD
      - service_id: ID of the service requested
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request, pk):
        date_str = request.query_params.get('date')
        service_id = request.query_params.get('service_id')

        if not date_str or not service_id:
            return Response(
                {"error": "Please provide 'date' and 'service_id' query parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            barber = Barber.objects.get(pk=pk, is_active=True)
            service = Service.objects.get(pk=service_id, is_active=True)
        except (Barber.DoesNotExist, Service.DoesNotExist):
            return Response({"error": "Barber or Service not found."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Get the schedule for that day of the week
        # Python weekday: 0=Monday, 6=Sunday
        day_of_week = target_date.weekday()
        schedule = barber.work_schedules.filter(day_of_week=day_of_week).first()

        if not schedule:
            return Response({"available_slots": []}, status=status.HTTP_200_OK)

        # 2. Find existing appointments for that day
        # We consider appointments that are not canceled or refunded as taking up time
        appointments = Appointment.objects.filter(
            barber=barber,
            date_time__date=target_date
        ).exclude(
            status__in=[
                Appointment.Status.CANCELED, 
                Appointment.Status.CANCELED_WITH_PENALTY, 
                Appointment.Status.REFUNDED
            ]
        )

        # 3. Generate possible slots
        # We'll generate slots every 15 minutes, but ensure the whole duration fits
        slots = []
        current_time_dt = datetime.combine(target_date, schedule.start_time)
        end_time_dt = datetime.combine(target_date, schedule.end_time)
        service_duration = timedelta(minutes=service.duration_minutes)

        while current_time_dt + service_duration <= end_time_dt:
            slot_start = current_time_dt
            slot_end = current_time_dt + service_duration
            
            is_available = True

            # Check past time (if today)
            if slot_start < timezone.now().replace(tzinfo=None):
                is_available = False

            # Check lunch break
            if is_available and schedule.break_start and schedule.break_end:
                break_start_dt = datetime.combine(target_date, schedule.break_start)
                break_end_dt = datetime.combine(target_date, schedule.break_end)
                
                # Overlap logic: (StartA < EndB) and (EndA > StartB)
                if slot_start < break_end_dt and slot_end > break_start_dt:
                    is_available = False

            # Check existing appointments
            if is_available:
                for appt in appointments:
                    appt_start = appt.date_time.replace(tzinfo=None)
                    appt_end = appt.end_time.replace(tzinfo=None)
                    if slot_start < appt_end and slot_end > appt_start:
                        is_available = False
                        break

            # Check Redis lock
            if is_available:
                slot_str = slot_start.strftime('%Y-%m-%dT%H:%M:%S')
                if is_slot_locked(barber.id, slot_str):
                    is_available = False

            if is_available:
                slots.append(slot_start.strftime('%H:%M'))

            # Increment by 15 minutes or by service duration
            # Standard in barbershops is to increment by the service duration or a fixed block (e.g. 15min)
            current_time_dt += timedelta(minutes=15)

        return Response({"available_slots": slots}, status=status.HTTP_200_OK)
