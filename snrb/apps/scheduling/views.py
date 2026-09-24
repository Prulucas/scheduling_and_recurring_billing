from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from apps.barbershop.models import Barber, Service
from .models import Appointment
from .serializers import AppointmentSerializer, CreateAppointmentSerializer
from .services import SchedulingService


class AppointmentListView(generics.ListAPIView):
    """
    List appointments. 
    Customers see their own. Barbers see their schedule.
    """
    serializer_class = AppointmentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        if user.role == 'CUSTOMER':
            return Appointment.objects.filter(customer=user.customer_profile).order_by('-date_time')
        elif user.role == 'BARBER':
            return Appointment.objects.filter(barber=user.barber_profile).order_by('date_time')
        return Appointment.objects.none()


class CreateAppointmentView(APIView):
    """
    Creates an appointment. Distinguishes between Subscription and Single Percentage (10% fee).
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        if request.user.role != 'CUSTOMER':
            return Response({"error": "Somente clientes podem agendar."}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = CreateAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        customer = request.user.customer_profile
        
        try:
            barber = Barber.objects.get(pk=data['barber_id'], is_active=True)
            service = Service.objects.get(pk=data['service_id'], is_active=True)
        except (Barber.DoesNotExist, Service.DoesNotExist):
            return Response({"error": "Barbeiro ou Serviço inválido."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if data['payment_type'] == Appointment.PaymentType.SUBSCRIPTION:
                appointment = SchedulingService.book_subscription_appointment(
                    customer, barber, service, data['date_time']
                )
            else:
                appointment = SchedulingService.book_single_appointment(
                    customer, barber, service, data['date_time']
                )
                
            return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CancelAppointmentView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
            
        # Ensure ownership
        if request.user.role == 'CUSTOMER' and appointment.customer != request.user.customer_profile:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.user.role == 'BARBER' and appointment.barber != request.user.barber_profile:
            return Response(status=status.HTTP_403_FORBIDDEN)
            
        reason = request.data.get('reason', '')
        
        try:
            SchedulingService.cancel_appointment(appointment, request.user, reason)
            return Response({"detail": "Agendamento cancelado."}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BarberActionView(APIView):
    """
    Base view for actions that only the Barber can perform on an appointment.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get_appointment(self, pk):
        if self.request.user.role != 'BARBER':
            raise ValidationError("Somente barbeiros podem realizar esta ação.")
            
        appointment = Appointment.objects.filter(pk=pk, barber=self.request.user.barber_profile).first()
        if not appointment:
            raise ValidationError("Agendamento não encontrado ou não pertence a você.")
        return appointment


class ApproveRefundView(BarberActionView):
    def patch(self, request, pk):
        try:
            appointment = self.get_appointment(pk)
            SchedulingService.approve_refund(appointment)
            return Response({"detail": "Reembolso aprovado e processado."}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class NoShowView(BarberActionView):
    def patch(self, request, pk):
        try:
            appointment = self.get_appointment(pk)
            SchedulingService.mark_no_show(appointment)
            return Response({"detail": "Falta registrada. Multa retida."}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CompleteAppointmentView(BarberActionView):
    def patch(self, request, pk):
        try:
            appointment = self.get_appointment(pk)
            if appointment.status != Appointment.Status.CONFIRMED:
                return Response({"error": "Somente agendamentos confirmados podem ser concluídos."}, status=status.HTTP_400_BAD_REQUEST)
                
            appointment.status = Appointment.Status.COMPLETED
            appointment.save()
            return Response({"detail": "Agendamento concluído."}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
